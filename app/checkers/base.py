from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.enums import CheckStatus, Layer
from app.models.responses import CheckResult
from app.models.crawl_data import CrawlData
from app.utils.html_helpers import safe_score


class BaseChecker(ABC):
    check_id: str
    check_number: int
    name: str
    layer: Layer

    @abstractmethod
    async def run(self, crawl: CrawlData) -> CheckResult:
        ...

    def _make_result(
        self,
        score: float,
        findings: list[str] | None = None,
        details: dict | None = None,
    ) -> CheckResult:
        score = safe_score(score)
        if score >= 80:
            status = CheckStatus.PASS
        elif score >= 50:
            status = CheckStatus.WARN
        else:
            status = CheckStatus.FAIL
        return CheckResult(
            check_id=self.check_id,
            check_number=self.check_number,
            name=self.name,
            layer=self.layer,
            score=score,
            status=status,
            findings=findings or [],
            details=details or {},
        )

    def _na_result(self, reason: str = "Not applicable") -> CheckResult:
        return CheckResult(
            check_id=self.check_id,
            check_number=self.check_number,
            name=self.name,
            layer=self.layer,
            score=0,
            status=CheckStatus.NA,
            findings=[reason],
        )
