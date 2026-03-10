from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class HttpsChecker(BaseChecker):
    check_id = "https"
    check_number = 6
    name = "HTTPS"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        if crawl.is_https:
            return self._make_result(100, ["https_enabled"])
        return self._make_result(0, ["not_https"])
