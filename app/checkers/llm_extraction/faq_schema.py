from __future__ import annotations

import json
import re

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

QUESTION_PATTERN = re.compile(
    r"^(what|how|why|when|where|who|which|can|do|does|is|are|should|will)\b",
    re.IGNORECASE,
)


class FaqSchemaChecker(BaseChecker):
    check_id = "faq_schema"
    check_number = 19
    name = "AI-Extractable Content Blocks"
    layer = Layer.LLM_EXTRACTION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        # Check for FAQPage JSON-LD
        has_faq_schema = False
        faq_items = 0
        scripts = crawl.soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                objects = []
                if isinstance(data, dict):
                    objects = data.get("@graph", [data])
                elif isinstance(data, list):
                    objects = data

                for obj in objects:
                    if obj.get("@type") == "FAQPage":
                        has_faq_schema = True
                        main_entity = obj.get("mainEntity", [])
                        if isinstance(main_entity, list):
                            faq_items = len(main_entity)
            except (json.JSONDecodeError, TypeError):
                pass

        if has_faq_schema:
            score += 35
            findings.append(f"faq_schema_present:{faq_items}_items")

        # Check for visible FAQ section in HTML
        faq_section = False
        for tag in crawl.soup.find_all(["h2", "h3", "h4"]):
            text = tag.get_text(strip=True).lower()
            if "faq" in text or "frequently asked" in text:
                faq_section = True
                break

        # Also check for FAQ by class/id
        faq_elements = crawl.soup.find_all(
            attrs={"class": re.compile(r"faq", re.I)}
        ) or crawl.soup.find_all(attrs={"id": re.compile(r"faq", re.I)})

        if faq_section or faq_elements:
            score += 20
            findings.append("visible_faq_section")

        # Q&A blocks: <details>/<summary> or question-like headings
        details = crawl.soup.find_all("details")
        question_headings = []
        for h in crawl.soup.find_all(["h2", "h3", "h4", "h5"]):
            text = h.get_text(strip=True)
            if text.endswith("?") or QUESTION_PATTERN.match(text):
                question_headings.append(text)

        if details:
            score += 15
            findings.append(f"details_summary_blocks:{len(details)}")
        if question_headings:
            score += 15
            findings.append(f"question_headings:{len(question_headings)}")

        # Self-contained answers: check if paragraphs after question headings
        # start with direct answers
        answer_quality = 0
        for h in crawl.soup.find_all(["h2", "h3", "h4"]):
            text = h.get_text(strip=True)
            if text.endswith("?") or QUESTION_PATTERN.match(text):
                sibling = h.find_next_sibling(["p", "div"])
                if sibling and len(sibling.get_text(strip=True)) > 30:
                    answer_quality += 1

        if answer_quality >= 3:
            score += 15
            findings.append("self_contained_answers")
        elif answer_quality >= 1:
            score += 8
            findings.append("partial_answer_quality")

        return self._make_result(
            score, findings,
            {"faq_schema_items": faq_items, "question_headings": len(question_headings)},
        )
