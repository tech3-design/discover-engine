from __future__ import annotations

import re

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

URL_PATTERN = re.compile(r"https?://\S+")


class LlmTxtChecker(BaseChecker):
    check_id = "llm_txt"
    check_number = 13
    name = "llms.txt Presence & Quality"
    layer = Layer.GRAPH_DISCOVERY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []

        if not crawl.llm_txt_content:
            findings.append("llm_txt_missing")
            return self._make_result(0, findings)

        content = crawl.llm_txt_content
        findings.append("llm_txt_exists")

        char_count = len(content.strip())
        has_urls = bool(URL_PATTERN.search(content))
        has_description = char_count > 200

        if has_description and has_urls:
            findings.append("llm_txt_comprehensive")
            return self._make_result(100, findings, {"length": char_count})

        if has_urls:
            findings.append("llm_txt_has_urls")
            return self._make_result(75, findings, {"length": char_count})

        if has_description:
            findings.append("llm_txt_descriptive_no_urls")
            return self._make_result(75, findings, {"length": char_count})

        findings.append("llm_txt_minimal")
        return self._make_result(40, findings, {"length": char_count})
