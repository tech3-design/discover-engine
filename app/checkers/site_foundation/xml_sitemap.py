from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class XmlSitemapChecker(BaseChecker):
    check_id = "xml_sitemap"
    check_number = 2
    name = "XML Sitemap"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []

        if crawl.sitemap_content is None:
            findings.append("sitemap_missing")
            return self._make_result(0, findings)

        content = crawl.sitemap_content
        findings.append("sitemap_exists")

        # Check valid XML with <url> or <sitemap> entries
        has_urls = "<url>" in content or "<sitemap>" in content
        has_xml_declaration = "<?xml" in content or "<urlset" in content or "<sitemapindex" in content

        if has_xml_declaration and has_urls:
            findings.append("valid_sitemap_with_urls")
            return self._make_result(100, findings, {"has_urls": True})
        elif has_xml_declaration:
            findings.append("valid_xml_no_urls")
            return self._make_result(50, findings, {"has_urls": False})
        else:
            findings.append("invalid_sitemap_format")
            return self._make_result(25, findings)
