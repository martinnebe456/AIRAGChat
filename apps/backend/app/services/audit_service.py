from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        actor_user_id: str | None,
        action_type: str,
        entity_type: str,
        entity_id: str | None = None,
        before_json=None,  # noqa: ANN001
        after_json=None,  # noqa: ANN001
        result: str = "success",
        reason: str | None = None,
        request: Request | None = None,
        trace_id: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            actor_user_id=actor_user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_json,
            after_json=after_json,
            result=result,
            reason=reason,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            trace_id=trace_id,
        )
        self.db.add(row)
        return row

