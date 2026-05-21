"""Per-request audit context propagated to SQLAlchemy listeners.

The audit listeners (`app/db/audit_listeners.py`) run inside `Session.flush()`
and have no access to the HTTP request. We bridge the two layers with a set of
`ContextVar`s populated by `AuditContextMiddleware` at the start of every
request and reset when the response is returned.

For non-HTTP contexts (CLI scripts, background jobs) the ContextVars stay at
their defaults — `user_id=None` causes the listener to skip writing audit rows
(the `audit_logs.user_id` column is NOT NULL), which is the desired behaviour:
those callers should opt in explicitly via `set_audit_user(...)` if they want
their changes attributed.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.security import decode_access_token


_user_id_var: ContextVar[int | None] = ContextVar("audit_user_id", default=None)
_ip_var: ContextVar[str | None] = ContextVar("audit_ip", default=None)
_ua_var: ContextVar[str | None] = ContextVar("audit_user_agent", default=None)


def get_audit_context() -> dict[str, Any]:
    """Return the currently active audit context (user_id / ip / user_agent)."""
    return {
        "user_id": _user_id_var.get(),
        "ip": _ip_var.get(),
        "user_agent": _ua_var.get(),
    }


def set_audit_user(user_id: int | None) -> None:
    """Override the audit user for the current async/thread context.

    Useful for background jobs, seed scripts, or tests that want their writes
    attributed to a specific user without going through HTTP middleware.
    """
    _user_id_var.set(user_id)


@contextmanager
def audit_as(
    user_id: int | None,
    *,
    ip: str | None = None,
    user_agent: str | None = "system",
) -> Iterator[None]:
    """Context manager that attributes any DB writes inside the block to
    ``user_id`` for the audit log. Designed for CLI scripts and background
    jobs that have no HTTP request to draw context from.

    Example::

        with audit_as(system_user_id):
            run_nightly_cleanup(db)
    """
    u_tok = _user_id_var.set(user_id)
    i_tok = _ip_var.set(ip)
    a_tok = _ua_var.set(user_agent)
    try:
        yield
    finally:
        _user_id_var.reset(u_tok)
        _ip_var.reset(i_tok)
        _ua_var.reset(a_tok)


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Populate the audit ContextVars from the inbound request.

    User id is best-effort: we decode the access cookie (or `Authorization:
    Bearer` header) without a database lookup. If decoding fails the audit
    listener simply skips writing rows for that request, which is preferable
    to blocking the request itself.
    """

    async def dispatch(self, request: Request, call_next):
        user_id = self._extract_user_id(request)
        ip = self._extract_ip(request)
        ua = request.headers.get("user-agent")

        u_tok = _user_id_var.set(user_id)
        i_tok = _ip_var.set(ip)
        a_tok = _ua_var.set(ua)
        try:
            return await call_next(request)
        finally:
            _user_id_var.reset(u_tok)
            _ip_var.reset(i_tok)
            _ua_var.reset(a_tok)

    @staticmethod
    def _extract_user_id(request: Request) -> int | None:
        token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
        if not token:
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1].strip()
        if not token:
            return None
        try:
            payload = decode_access_token(token)
        except Exception:
            return None
        sub = payload.get("sub")
        if sub is None:
            return None
        try:
            return int(sub)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_ip(request: Request) -> str | None:
        # Honor X-Forwarded-For when a trusted proxy / load balancer is in front.
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip() or None
        return request.client.host if request.client else None
