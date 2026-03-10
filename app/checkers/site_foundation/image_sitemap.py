from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class ImageSitemapChecker(BaseChecker):
    check_id = "image_sitemap"
    check_number = 3
    name = "Image Sitemap"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []

        # Check sitemap content for image tags
        if crawl.sitemap_content and "<image:image>" in crawl.sitemap_content:
            findings.append("image_tags_in_sitemap")
            return self._make_result(100, findings)

        findings.append("no_image_sitemap")
        return self._make_result(0, findings)
