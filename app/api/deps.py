from __future__ import annotations

from functools import lru_cache

from app.services.audit_service import AuditService
from app.store.audit_store import AuditStore

_store = AuditStore()
_audit_service = AuditService(_store)


def get_store() -> AuditStore:
    return _store


def get_audit_service() -> AuditService:
    return _audit_service
