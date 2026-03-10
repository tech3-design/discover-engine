from __future__ import annotations

from app.models.responses import AuditResponse


class AuditStore:
    """In-memory audit result store. Swappable to Redis later."""

    def __init__(self) -> None:
        self._store: dict[str, AuditResponse] = {}

    def get(self, audit_id: str) -> AuditResponse | None:
        return self._store.get(audit_id)

    def set(self, audit_id: str, response: AuditResponse) -> None:
        self._store[audit_id] = response

    def delete(self, audit_id: str) -> None:
        self._store.pop(audit_id, None)
