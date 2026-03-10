from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

SESSION_PATTERNS = re.compile(
    r"(session_?id|sid|phpsessid|jsessionid|token)=", re.IGNORECASE
)
CALENDAR_PATTERN = re.compile(r"/\d{4}/\d{2}(/\d{2})?/?$")
FACET_THRESHOLD = 3  # More than N query params = possible facet combo


class CrawlTrapsChecker(BaseChecker):
    check_id = "crawl_traps"
    check_number = 8
    name = "Crawl Trap Prevention"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        issues = 0

        # Check internal links for traps
        for link in crawl.internal_links[:100]:  # sample
            parsed = urlparse(link)

            # Session IDs in URLs
            if SESSION_PATTERNS.search(link):
                issues += 1
                if "session_ids_in_urls" not in findings:
                    findings.append("session_ids_in_urls")

            # Infinite calendar patterns
            if CALENDAR_PATTERN.search(parsed.path):
                issues += 1
                if "calendar_pattern_detected" not in findings:
                    findings.append("calendar_pattern_detected")

            # Too many query params (facet explosion)
            params = parse_qs(parsed.query)
            if len(params) > FACET_THRESHOLD:
                issues += 1
                if "excessive_url_params" not in findings:
                    findings.append("excessive_url_params")

        if issues == 0:
            findings.append("no_crawl_traps_detected")
            return self._make_result(100, findings)

        # Graduated scoring
        score = max(0, 100 - issues * 15)
        return self._make_result(score, findings, {"trap_issues": issues})
