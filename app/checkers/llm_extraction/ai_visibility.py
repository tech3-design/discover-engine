"""AI Visibility checker (#22) — discovers how extractable content is for LLMs.

Pure static analysis. Finds: answer-first patterns, citation formatting,
self-contained vs dependent paragraphs, takeaway blocks, definition
patterns, quotable sentences, and content chunking via headings.
"""
from __future__ import annotations

import re

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

ANSWER_FIRST_PATTERNS = [
    r"^(?:the\s+)?(?:short\s+)?answer\s+is\b",
    r"^(?:in\s+short|simply\s+put|to\s+summarize|in\s+summary|tl;?dr)\b",
    r"^(?:yes|no)[,.]",
    r"^(?:\w+\s+){1,10}(?:is|are|was|were|means?|refers?\s+to)\b",
]

CITATION_QUALITY_PATTERNS = [
    r"according to\b",
    r"\(\w[\w\s&.,]+\d{4}\)",
    r"\[\d+\]",
    r"\bsource:\s",
    r"\bas reported by\b",
    r"\bresearch (?:by|from|shows)\b",
    r"\bstudy (?:by|from|shows|found)\b",
]

DEPENDENCY_PATTERNS = [
    r"\bas mentioned (?:above|earlier|previously|before)\b",
    r"\bsee (?:above|below|the (?:next|previous|following))\b",
    r"\bas (?:we|I) (?:discussed|noted|mentioned|said|stated)\b",
    r"\brefer(?:ring)? to the (?:above|previous|following)\b",
    r"\bas shown (?:above|below)\b",
    r"\bin the (?:previous|next|following) section\b",
]

DEFINITION_PATTERNS = [
    r"\b\w+(?:\s+\w+){0,3}\s+is defined as\b",
    r"\b\w+(?:\s+\w+){0,3}\s+refers? to\b",
    r"\b\w+(?:\s+\w+){0,3}\s+means?\b",
    r"\b(?:defined|known) as\b",
    r"\b\w+(?:\s+\w+){0,3}\s+is (?:a|an|the) (?:process|method|technique|approach|concept|framework|system|tool|platform)\b",
]

GENERIC_HEADINGS = {
    "introduction", "overview", "summary", "conclusion", "details",
    "more", "read more", "learn more", "resources", "links",
    "other", "misc", "miscellaneous", "general", "info", "information",
}


class AiVisibilityChecker(BaseChecker):
    check_id = "ai_visibility"
    check_number = 22
    name = "AI Visibility"
    layer = Layer.LLM_EXTRACTION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        details: dict = {}
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        soup = crawl.soup
        text = crawl.text
        text_lower = text.lower()

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
                findings.append("ai_answer_first_detected")
                score += 15
            else:
                findings.append("ai_no_answer_first")

        # ── Citation format quality ────────────────────────────────────
        citation_count = 0
        for p in CITATION_QUALITY_PATTERNS:
            citation_count += len(re.findall(p, text, re.I))
        details["ai_citation_count"] = citation_count
        if citation_count > 0:
            findings.append(f"ai_citations_found:{citation_count}")
            score += min(15, citation_count * 3)
        else:
            findings.append("ai_no_citations")

        # ── Self-contained paragraphs ──────────────────────────────────
        dependency_matches: list[str] = []
        for p in DEPENDENCY_PATTERNS:
            for m in re.finditer(p, text_lower):
                dependency_matches.append(m.group())
        details["dependency_language"] = dependency_matches[:10]
        details["dependency_count"] = len(dependency_matches)
        if len(dependency_matches) == 0:
            findings.append("ai_paragraphs_self_contained")
            score += 15
        else:
            findings.append(f"ai_dependency_language_found:{len(dependency_matches)}")
            score += max(0, 15 - len(dependency_matches) * 3)

        # ── Key takeaway blocks ────────────────────────────────────────
        takeaway_re = re.compile(
            r"(summary|tl;?dr|key (?:takeaway|point|finding)|in summary|conclusion|highlights|quick (?:summary|overview))",
            re.I,
        )
        takeaway_headings: list[str] = []
        for h in soup.find_all(re.compile(r"^h[2-4]$")):
            h_text = h.get_text(strip=True)
            if takeaway_re.search(h_text):
                takeaway_headings.append(h_text)

        aside_count = len(soup.find_all("aside"))
        callout_count = 0
        for cls_pattern in ["callout", "highlight", "takeaway", "key-point", "summary-box", "tldr"]:
            callout_count += len(soup.find_all(class_=re.compile(cls_pattern, re.I)))

        details["takeaway_headings"] = takeaway_headings
        details["aside_elements"] = aside_count
        details["callout_elements"] = callout_count

        has_takeaways = bool(takeaway_headings) or aside_count > 0 or callout_count > 0
        if has_takeaways:
            findings.append("ai_takeaway_blocks_found")
            score += 15
        else:
            findings.append("ai_no_takeaway_blocks")

        # ── Definition patterns ────────────────────────────────────────
        definitions_found: list[str] = []
        for p in DEFINITION_PATTERNS:
            for m in re.finditer(p, text, re.I):
                definitions_found.append(m.group().strip()[:80])
        details["definitions_found"] = definitions_found[:10]
        details["definition_count"] = len(definitions_found)
        if definitions_found:
            findings.append(f"ai_definitions_found:{len(definitions_found)}")
            score += min(15, len(definitions_found) * 3)
        else:
            findings.append("ai_no_definitions")

        # ── Quotability ────────────────────────────────────────────────
        sentences = re.split(r"[.!?]+", text)
        quotable_sentences: list[str] = []
        for sent in sentences:
            sent_stripped = sent.strip()
            words = sent_stripped.split()
            word_len = len(words)
            if 10 <= word_len <= 30:
                sent_lower = sent_stripped.lower()
                if not sent_lower.startswith(("how ", "what ", "why ", "when ", "where ", "who ")):
                    if re.search(r"\b(?:is|are|was|were|has|have|shows?|indicates?|means?|provides?|requires?|includes?)\b", sent_lower):
                        quotable_sentences.append(sent_stripped[:100])

        details["quotable_sentences"] = quotable_sentences[:10]
        details["quotable_count"] = len(quotable_sentences)
        if quotable_sentences:
            findings.append(f"ai_quotable_sentences:{len(quotable_sentences)}")
            score += min(15, len(quotable_sentences) * 2)
        else:
            findings.append("ai_no_quotable_sentences")

        # ── Content chunking (headings) ────────────────────────────────
        headings = soup.find_all(re.compile(r"^h[2-3]$"))
        heading_texts: list[str] = []
        descriptive_headings: list[str] = []
        generic_headings: list[str] = []

        for h in headings:
            h_text = h.get_text(strip=True)
            heading_texts.append(h_text)
            if h_text.lower() not in GENERIC_HEADINGS and len(h_text.split()) >= 2:
                descriptive_headings.append(h_text)
            else:
                generic_headings.append(h_text)

        details["h2_h3_headings"] = heading_texts
        details["descriptive_headings"] = len(descriptive_headings)
        details["generic_headings"] = generic_headings

        if heading_texts:
            findings.append(f"ai_headings_found:{len(heading_texts)}")
            if descriptive_headings:
                findings.append(f"ai_descriptive_headings:{len(descriptive_headings)}")
            if generic_headings:
                findings.append(f"ai_generic_headings:{len(generic_headings)}")
            desc_ratio = len(descriptive_headings) / len(heading_texts) if heading_texts else 0
            score += min(10, int(desc_ratio * 10))
        else:
            findings.append("ai_no_headings")

        return self._make_result(score, findings, details)
