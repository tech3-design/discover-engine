from __future__ import annotations

from pydantic import BaseModel

from .enums import AuditStatus, CheckStatus, Layer


class CheckResult(BaseModel):
    check_id: str
    check_number: int
    name: str
    layer: Layer
    score: float
    status: CheckStatus
    findings: list[str] = []
    details: dict = {}


class LayerResult(BaseModel):
    layer: Layer
    label: str
    weight: float
    score: float
    grade: str
    checks: list[CheckResult]


class SignalScore(BaseModel):
    overall_score: float
    grade: str
    layers: list[LayerResult]


class AuditResponse(BaseModel):
    audit_id: str
    url: str
    status: AuditStatus
    signal_score: SignalScore | None = None
    error: str | None = None
