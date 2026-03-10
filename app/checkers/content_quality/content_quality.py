"""Content Quality checker (#20) — discovers content quality signals.

Extracts and reports: citations, statistics, expert quotes, authoritative
language, readability metrics, technical terminology, vocabulary diversity,
content structure, answer-first format, and keyword repetition.
"""
from __future__ import annotations

import re
from collections import Counter

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

try:
    import textstat
except ImportError:
    textstat = None  # type: ignore[assignment]

# ── Regex patterns ported from Django content.py ────────────────────────

CITATION_PATTERNS = [
    r"according to\b",
    r"\bcited? (?:by|in|from)\b",
    r"\(\w[\w\s&.,]+\d{4}\)",
    r"\[\d+\]",
    r"\bsource:\s",
    r"\breference:\s",
    r"\bas reported by\b",
    r"\bpublished (?:in|by)\b",
    r"\bresearch (?:by|from|shows)\b",
    r"\bstudy (?:by|from|shows|found)\b",
    r"\bdata from\b",
]

STAT_PATTERNS = [
    r"\d+(?:\.\d+)?%",
    r"\$\d[\d,.]*\s*(?:billion|million|trillion|thousand|B|M|K)?",
    r"\d[\d,.]*\s*(?:billion|million|trillion|thousand)",
    r"\d+x\s+(?:more|faster|slower|better|higher|lower|increase|growth)",
    r"\b(?:increased?|decreased?|grew?|rose|fell|dropped?)\s+(?:by\s+)?\d",
    r"\d+\s*(?:out of|/)\s*\d+",
    r"\b(?:average|median|mean)\s+(?:of\s+)?\d",
    r"\d+(?:\.\d+)?\s*(?:per ?cent|percent)",
]

QUOTE_PATTERNS = [
    r"['\u2018\u201C\"][\w\s]{15,}['\u2019\u201D\"]\s*(?:,?\s*(?:says?|said|explains?|notes?|argues?|according to|wrote|states?))",
    r"(?:says?|said|explains?|notes?|argues?|wrote|states?)\s+[\w\s]+[,:]?\s*['\u2018\u201C\"]",
    r"['\u2018\u201C\"][\w\s]{15,}['\u2019\u201D\"]\s*[-\u2014\u2013]\s*\w",
]

AUTHORITY_PATTERNS = [
    r"\b(?:demonstrably|definitively|conclusively|systematically)\b",
    r"\bbased on (?:our|my|the) (?:analysis|research|data|findings|testing)\b",
    r"\b(?:our|my) (?:research|analysis|data|findings|testing) (?:shows?|reveals?|indicates?|confirms?|demonstrates?)\b",
    r"\b(?:evidence|data) (?:shows?|suggests?|indicates?|confirms?)\b",
    r"\b(?:it is|it's) (?:clear|evident|well.established|proven|documented)\b",
    r"\b(?:critical|essential|fundamental|imperative)\s+(?:to|that|for)\b",
    r"\b(?:best practice|industry standard|proven (?:method|approach|strategy))\b",
    r"\b(?:we (?:recommend|advise|suggest)|(?:should|must) (?:be|ensure|implement))\b",
]

HEDGING_PATTERNS = [
    r"\b(?:i think|i guess|maybe|perhaps|possibly|might be|could be|not sure)\b",
    r"\b(?:it seems like|sort of|kind of|in my opinion)\b",
    r"\b(?:i believe|i feel|i suppose)\b",
]

ANSWER_FIRST_PATTERNS = [
    r"^(?:the\s+)?(?:short\s+)?answer\s+is\b",
    r"^(?:in\s+short|simply\s+put|to\s+summarize|in\s+summary|tl;?dr)\b",
    r"^(?:yes|no)[,.]",
    r"^(?:\w+\s+){1,10}(?:is|are|was|were|means?|refers?\s+to)\b",
]

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "as", "if", "so", "not", "no", "can",
    "will", "do", "you", "we", "he", "she", "they", "have", "has", "had",
}

TRANSITION_WORDS = [
    r"\bhowever\b", r"\btherefore\b", r"\bmoreover\b", r"\bfurthermore\b",
    r"\bin addition\b", r"\bconsequently\b", r"\bas a result\b",
    r"\bon the other hand\b", r"\bin contrast\b", r"\bfor (?:example|instance)\b",
    r"\bspecifically\b", r"\bnotably\b", r"\bimportantly\b",
]


def _count_pattern_matches(text: str, patterns: list[str]) -> int:
    count = 0
    for p in patterns:
        count += len(re.findall(p, text, re.I))
    return count


def _count_words(text: str) -> int:
    return len(text.split())


class ContentQualityChecker(BaseChecker):
    check_id = "content_quality"
    check_number = 20
    name = "Content Quality"
    layer = Layer.CONTENT_QUALITY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        details: dict = {}
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        text = crawl.text
        text_lower = text.lower()
        soup = crawl.soup
        word_count = _count_words(text)
        details["word_count"] = word_count

        # ── Citations ──────────────────────────────────────────────────
        citation_count = _count_pattern_matches(text, CITATION_PATTERNS)
        # Check for reference/bibliography sections
        ref_section_found = False
        for tag in soup.find_all(re.compile(r"^h[2-4]$")):
            tag_text = tag.get_text(strip=True).lower()
            if tag_text in ("references", "sources", "bibliography", "works cited", "citations"):
                ref_section_found = True
                citation_count += 3
        details["citation_count"] = citation_count
        details["has_reference_section"] = ref_section_found
        if citation_count > 0:
            findings.append(f"citations_found:{citation_count}")
            score += min(15, citation_count * 3)
        else:
            findings.append("no_citations_found")
        if ref_section_found:
            findings.append("reference_section_found")

        # ── Statistics & data points ───────────────────────────────────
        stat_count = _count_pattern_matches(text, STAT_PATTERNS)
        details["statistic_count"] = stat_count
        if stat_count > 0:
            findings.append(f"statistics_found:{stat_count}")
            score += min(12, stat_count * 2)
        else:
            findings.append("no_statistics_found")

        # ── Expert quotes & blockquotes ────────────────────────────────
        quote_count = _count_pattern_matches(text, QUOTE_PATTERNS)
        blockquote_count = len(soup.find_all("blockquote"))
        total_quotes = quote_count + blockquote_count
        details["attributed_quotes"] = quote_count
        details["blockquote_elements"] = blockquote_count
        if total_quotes > 0:
            findings.append(f"quotes_found:{total_quotes}")
            score += min(10, total_quotes * 3)
        else:
            findings.append("no_quotes_found")
        if blockquote_count > 0:
            findings.append(f"blockquotes_found:{blockquote_count}")

        # ── Authoritative vs hedging language ──────────────────────────
        authority_count = _count_pattern_matches(text_lower, AUTHORITY_PATTERNS)
        hedge_count = _count_pattern_matches(text_lower, HEDGING_PATTERNS)
        details["authority_signals"] = authority_count
        details["hedging_signals"] = hedge_count
        if authority_count > 0:
            findings.append(f"authority_signals_found:{authority_count}")
        if hedge_count > 0:
            findings.append(f"hedging_signals_found:{hedge_count}")
        net = authority_count - hedge_count
        if net >= 2:
            score += 10
        elif net >= 0 and authority_count > 0:
            score += 5
        if authority_count == 0 and hedge_count == 0:
            findings.append("no_tone_signals")

        # ── Readability metrics ────────────────────────────────────────
        if textstat and len(text) > 100:
            fk_grade = textstat.flesch_kincaid_grade(text)
            flesch_ease = textstat.flesch_reading_ease(text)
            details["fk_grade"] = round(fk_grade, 1)
            details["flesch_ease"] = round(flesch_ease, 1)
            findings.append(f"readability_grade:{details['fk_grade']}")
            findings.append(f"readability_ease:{details['flesch_ease']}")
            if 6 <= fk_grade <= 12 and flesch_ease >= 60:
                score += 10
            elif 4 <= fk_grade <= 14 and flesch_ease >= 40:
                score += 6
            else:
                score += 2
        else:
            details["fk_grade"] = None
            details["flesch_ease"] = None
            score += 5

        # ── Technical terminology ──────────────────────────────────────
        acronym_definitions = re.findall(
            r"\b[A-Z][a-z]+(?:[\s-][A-Z][a-z]+)+\s*\([A-Z]{2,}\)", text
        )
        standalone_acronyms = set(re.findall(r"\b[A-Z]{3,}\b", text))
        common_words = {
            "THE", "AND", "FOR", "NOT", "BUT", "ARE", "WAS", "HAS", "HIS", "HER",
            "ITS", "ALL", "CAN", "HAD", "HIM", "WHO", "DID", "GET", "HOW", "MAY",
            "NEW", "NOW", "OLD", "OUR", "OWN", "SAY", "SHE", "TOO", "USE", "FAQ",
        }
        technical_acronyms = sorted(standalone_acronyms - common_words)
        compound_terms = re.findall(
            r"\b\w+-(?:based|driven|powered|enabled|focused|oriented|specific|level|aware)\b",
            text_lower,
        )
        details["acronym_definitions"] = acronym_definitions[:10]
        details["technical_acronyms"] = technical_acronyms[:20]
        details["compound_terms"] = compound_terms[:10]
        tech_total = len(acronym_definitions) + len(technical_acronyms) + len(compound_terms)
        details["technical_term_count"] = tech_total
        if tech_total > 0:
            findings.append(f"technical_terms_found:{tech_total}")
            score += min(8, tech_total)
        else:
            findings.append("no_technical_terms_found")
        if acronym_definitions:
            findings.append(f"acronym_definitions_found:{len(acronym_definitions)}")

        # ── Vocabulary diversity ───────────────────────────────────────
        if word_count >= 50:
            words = re.findall(r"\b[a-z]{3,}\b", text_lower)
            if words:
                sample = words[:500]
                ttr = len(set(sample)) / len(sample)
                details["vocabulary_ttr"] = round(ttr, 3)
                details["unique_words_sampled"] = len(set(sample))
                findings.append(f"vocabulary_ttr:{details['vocabulary_ttr']}")
                if ttr >= 0.50:
                    score += 8
                elif ttr >= 0.35:
                    score += 4
        else:
            details["vocabulary_ttr"] = None

        # ── Content structure ──────────────────────────────────────────
        findings.append(f"word_count:{word_count}")

        paragraphs = soup.find_all("p")
        para_lengths = [_count_words(p.get_text()) for p in paragraphs if p.get_text(strip=True)]
        details["paragraph_count"] = len(para_lengths)
        if para_lengths:
            avg_para = sum(para_lengths) / len(para_lengths)
            details["avg_paragraph_words"] = round(avg_para, 1)
            findings.append(f"paragraph_avg_words:{details['avg_paragraph_words']}")
            if 20 <= avg_para <= 80:
                score += 4
            elif 15 <= avg_para <= 120:
                score += 2

        transition_count = sum(len(re.findall(p, text_lower)) for p in TRANSITION_WORDS)
        details["transition_word_count"] = transition_count
        if transition_count > 0:
            findings.append(f"transition_words_found:{transition_count}")
            score += min(4, transition_count)

        list_count = len(soup.find_all(["ul", "ol"]))
        table_count = len(soup.find_all("table"))
        details["list_count"] = list_count
        details["table_count"] = table_count
        if list_count > 0:
            findings.append(f"lists_found:{list_count}")
        if table_count > 0:
            findings.append(f"tables_found:{table_count}")

        # ── Answer-first format ────────────────────────────────────────
        first_p = soup.find("p")
        if first_p:
            first_text = first_p.get_text(strip=True)
            first_lower = first_text.lower()[:200]
            first_words = len(first_text.split())
            details["first_paragraph_words"] = first_words
            details["first_paragraph_preview"] = first_text[:120]
            answer_first = False
            for pattern in ANSWER_FIRST_PATTERNS:
                if re.search(pattern, first_lower, re.I):
                    answer_first = True
                    break
            if not answer_first and 20 <= first_words <= 60:
                if any(w in first_lower for w in ["is ", "are ", "means ", "refers "]):
                    answer_first = True
            if answer_first:
                findings.append("answer_first_detected")
                score += 10
            else:
                findings.append("no_answer_first_detected")

        # ── Keyword repetition ─────────────────────────────────────────
        if word_count >= 100:
            words_list = [w for w in re.findall(r"\b[a-z]{2,}\b", text_lower) if w not in _STOP_WORDS]
            bigrams = [f"{words_list[i]} {words_list[i+1]}" for i in range(len(words_list) - 1)]
            if bigrams:
                bigram_counts = Counter(bigrams)
                top_bigram, top_count = bigram_counts.most_common(1)[0]
                stuffing_ratio = top_count / len(bigrams)
                details["top_bigram"] = top_bigram
                details["top_bigram_frequency"] = round(stuffing_ratio, 4)
                details["top_bigram_count"] = top_count
                findings.append(f"top_bigram:{top_bigram} ({top_count}x, {stuffing_ratio:.1%})")
                if stuffing_ratio > 0.03:
                    findings.append("keyword_stuffing_detected")
                    score -= 5

        return self._make_result(score, findings, details)
