from __future__ import annotations

from urllib.parse import urlparse

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class CanonicalTagsChecker(BaseChecker):
    check_id = "canonical_tags"
    check_number = 7
    name = "Canonical Tags"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        canonicals = crawl.soup.find_all("link", rel="canonical")
        if not canonicals:
            findings.append("no_canonical_tag")
            return self._make_result(0, findings)

        score += 50
        findings.append("canonical_tag_present")

        # Check self-referencing
        href = canonicals[0].get("href", "")
        page_parsed = urlparse(crawl.url)
        canon_parsed = urlparse(href)

        is_self_ref = (
            page_parsed.netloc == canon_parsed.netloc
            and page_parsed.path.rstrip("/") == canon_parsed.path.rstrip("/")
        )
        if is_self_ref:
            score += 30
            findings.append("self_referencing_canonical")
        else:
            findings.append("canonical_points_elsewhere")

        # Check for conflicts (multiple different canonicals)
        if len(canonicals) > 1:
            hrefs = {c.get("href", "") for c in canonicals}
            if len(hrefs) > 1:
                findings.append("conflicting_canonicals")
            else:
                score += 20
                findings.append("no_conflicts")
        else:
            score += 20
            findings.append("single_canonical")

        return self._make_result(score, findings)
