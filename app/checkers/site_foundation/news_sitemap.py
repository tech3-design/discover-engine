from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class NewsSitemapChecker(BaseChecker):
    check_id = "news_sitemap"
    check_number = 5
    name = "News Sitemap"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []

        # Detect if site has news-like content
        is_news_site = False
        if crawl.soup:
            # Check for article tags, news schema, publication dates
            articles = crawl.soup.find_all("article")
            time_tags = crawl.soup.find_all("time")
            news_schema = "NewsArticle" in crawl.html if crawl.html else False
            is_news_site = len(articles) >= 2 or news_schema or len(time_tags) >= 3

        if not is_news_site:
            return self._na_result("Site does not appear to be news-oriented")

        if crawl.sitemap_content and "<news:news>" in crawl.sitemap_content:
            findings.append("news_sitemap_found")
            return self._make_result(100, findings)

        findings.append("news_site_no_news_sitemap")
        return self._make_result(0, findings)
