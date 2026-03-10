from __future__ import annotations

import re

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

SEMANTIC_TAGS = ["article", "main", "nav", "section", "header", "footer", "aside"]


class SemanticHtmlChecker(BaseChecker):
    check_id = "semantic_html"
    check_number = 15
    name = "Semantic HTML & DOM"
    layer = Layer.NODE_READABILITY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        # Check semantic tag usage
        found_tags: list[str] = []
        for tag in SEMANTIC_TAGS:
            if crawl.soup.find(tag):
                found_tags.append(tag)

        tag_ratio = len(found_tags) / len(SEMANTIC_TAGS)
        score += tag_ratio * 40
        findings.append(f"semantic_tags:{','.join(found_tags)}")

        # Heading hierarchy
        headings = crawl.soup.find_all(re.compile(r"^h[1-6]$"))
        if headings:
            h1s = [h for h in headings if h.name == "h1"]

            # Single H1
            if len(h1s) == 1:
                score += 15
                findings.append("single_h1")
            elif len(h1s) > 1:
                score += 5
                findings.append(f"multiple_h1s:{len(h1s)}")
            else:
                findings.append("no_h1")

            # Check hierarchy (no jumps > 1 level)
            levels = [int(h.name[1]) for h in headings]
            has_jump = False
            for i in range(1, len(levels)):
                if levels[i] > levels[i - 1] + 1:
                    has_jump = True
                    break

            if not has_jump:
                score += 15
                findings.append("valid_heading_hierarchy")
            else:
                score += 5
                findings.append("heading_hierarchy_gaps")

            findings.append(f"heading_count:{len(headings)}")
        else:
            findings.append("no_headings")

        # Check for meaningful structure
        lists = crawl.soup.find_all(["ul", "ol"])
        tables = crawl.soup.find_all("table")

        if lists:
            score += 15
            findings.append(f"lists_present:{len(lists)}")
        if tables:
            score += 15
            findings.append(f"tables_present:{len(tables)}")

        return self._make_result(score, findings, {"semantic_tags": found_tags})
