from __future__ import annotations

import re

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class RobotsMetaChecker(BaseChecker):
    check_id = "robots_meta"
    check_number = 9
    name = "Robots Meta Tags"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        meta_robots = crawl.soup.find_all("meta", attrs={"name": re.compile(r"robots", re.I)})

        if not meta_robots:
            # No robots meta = good, nothing blocking
            findings.append("no_robots_meta_tag")
            return self._make_result(100, findings)

        content_values = []
        for tag in meta_robots:
            content = tag.get("content", "").lower()
            content_values.append(content)

        has_noindex = any("noindex" in c for c in content_values)
        has_nofollow = any("nofollow" in c for c in content_values)

        if has_noindex:
            findings.append("noindex_directive")
            return self._make_result(0, findings)

        if has_nofollow:
            findings.append("nofollow_directive")
            return self._make_result(50, findings)

        # Check for conflicting directives (index + noindex)
        all_content = " ".join(content_values)
        if "index" in all_content and "noindex" in all_content:
            findings.append("conflicting_directives")
            return self._make_result(50, findings)

        findings.append("robots_meta_ok")
        return self._make_result(100, findings)
