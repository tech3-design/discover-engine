from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class VideoSitemapChecker(BaseChecker):
    check_id = "video_sitemap"
    check_number = 4
    name = "Video Sitemap"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []

        if crawl.sitemap_content and "<video:video>" in crawl.sitemap_content:
            findings.append("video_tags_in_sitemap")
            return self._make_result(100, findings)

        findings.append("no_video_sitemap")
        return self._make_result(0, findings)
