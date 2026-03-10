from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import get_audit_service
from app.models.enums import AuditStatus
from app.models.requests import DiscoverRequest
from app.services.audit_service import AuditService
from app.services.report_service import build_report

router = APIRouter()


@router.post("/discover", status_code=202)
async def start_audit(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks,
    service: AuditService = Depends(get_audit_service),
):
    url = str(request.url)
    audit_id = service.create_audit(url)
    background_tasks.add_task(_run_audit_wrapper, service, audit_id)
    return {"audit_id": audit_id, "status": "pending", "url": url}


async def _run_audit_wrapper(service: AuditService, audit_id: str) -> None:
    """Wrapper to ensure the audit coroutine runs properly in the background."""
    await service.run_audit(audit_id)


@router.get("/discover/{audit_id}/status")
async def audit_status(
    audit_id: str,
    service: AuditService = Depends(get_audit_service),
):
    audit = service.store.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return {"audit_id": audit_id, "status": audit.status, "url": audit.url}


@router.get("/discover/{audit_id}/results")
async def audit_results(
    audit_id: str,
    service: AuditService = Depends(get_audit_service),
):
    audit = service.store.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.status not in (AuditStatus.COMPLETED, AuditStatus.FAILED):
        raise HTTPException(
            status_code=202,
            detail=f"Audit still in progress: {audit.status}",
        )
    return audit


@router.get("/discover/{audit_id}/report")
async def audit_report(
    audit_id: str,
    service: AuditService = Depends(get_audit_service),
):
    audit = service.store.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.status not in (AuditStatus.COMPLETED, AuditStatus.FAILED):
        raise HTTPException(
            status_code=202,
            detail=f"Audit still in progress: {audit.status}",
        )
    return build_report(audit)
