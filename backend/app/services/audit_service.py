"""Explicit audit recording for semantic actions.

The SQLAlchemy listeners in `app/db/audit_listeners.py` cover raw CRUD on the
audited models automatically. Use `AuditService.record(...)` from service /
route layers when you want to log a *business* action that isn't a 1:1 column
diff — for example a workflow transition triggered by a side-effecting RPC
that doesn't actually mutate the row, or an action the listener can't infer
unambiguously from the diff.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.audit_context import get_audit_context
from app.models.audit.audit_log import AuditAction, AuditLog, AuditModule


class AuditService:
    @staticmethod
    def record(
        db: Session,
        *,
        module: AuditModule,
        action: AuditAction,
        record_id: int,
        user_id: int | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog | None:
        """Append an audit row to `db`. Returns None when no user can be
        attributed (the NOT NULL constraint on `user_id` would otherwise
        fail). The caller is responsible for committing `db`.
        """
        ctx = get_audit_context()
        resolved_user = user_id if user_id is not None else ctx.get("user_id")
        if not resolved_user:
            return None

        entry = AuditLog(
            user_id=resolved_user,
            module=module,
            action=action,
            record_id=record_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address if ip_address is not None else ctx.get("ip"),
            user_agent=user_agent if user_agent is not None else ctx.get("user_agent"),
        )
        db.add(entry)
        return entry
