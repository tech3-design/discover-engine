from __future__ import annotations

import asyncio
import uuid

import structlog

from app.checkers.registry import registry
from app.models.enums import AuditStatus
from app.models.responses import AuditResponse
from app.services.crawler_service import crawl_url
from app.services.scoring_service import compute_signal_score
from app.store.audit_store import AuditStore

logger = structlog.get_logger()


class AuditService:
    def __init__(self, store: AuditStore) -> None:
        self.store = store

    def create_audit(self, url: str) -> str:
        audit_id = uuid.uuid4().hex[:12]
        self.store.set(
            audit_id,
            AuditResponse(
                audit_id=audit_id, url=url, status=AuditStatus.PENDING
            ),
        )
        return audit_id

    async def run_audit(self, audit_id: str) -> None:
        audit = self.store.get(audit_id)
        if not audit:
            return

        try:
            # Phase 1 — Crawl
            self.store.set(
                audit_id, audit.model_copy(update={"status": AuditStatus.CRAWLING})
            )
            crawl = await crawl_url(audit.url)
            if crawl.error:
                self.store.set(
                    audit_id,
                    audit.model_copy(
                        update={"status": AuditStatus.FAILED, "error": crawl.error}
                    ),
                )
                return

            # Phase 2 — Run all checkers concurrently
            self.store.set(
                audit_id, audit.model_copy(update={"status": AuditStatus.ANALYZING})
            )
            checkers = registry.all()
            results = await asyncio.gather(
                *(c.run(crawl) for c in checkers), return_exceptions=True
            )

            # Collect valid results, log exceptions
            check_results = []
            for checker, result in zip(checkers, results):
                if isinstance(result, Exception):
                    logger.error(
                        "checker_failed",
                        checker=checker.check_id,
                        error=str(result),
                    )
                else:
                    check_results.append(result)

            # Phase 3 — Score
            signal_score = compute_signal_score(check_results)

            self.store.set(
                audit_id,
                AuditResponse(
                    audit_id=audit_id,
                    url=audit.url,
                    status=AuditStatus.COMPLETED,
                    signal_score=signal_score,
                ),
            )
            logger.info(
                "audit_completed",
                audit_id=audit_id,
                score=signal_score.overall_score,
                grade=signal_score.grade,
            )

        except Exception as exc:
            logger.exception("audit_error", audit_id=audit_id)
            self.store.set(
                audit_id,
                AuditResponse(
                    audit_id=audit_id,
                    url=audit.url,
                    status=AuditStatus.FAILED,
                    error=str(exc),
                ),
            )
