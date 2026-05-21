"""CSRF protection (double-submit cookie pattern).

Strategy:
- On login/refresh the backend sets a `csrf_token` cookie *without* HttpOnly,
  so the SPA's JS can read it.
- For every state-changing request (POST/PUT/PATCH/DELETE) that authenticates
  via the access-token *cookie*, the SPA must echo the same value back in the
  `X-CSRF-Token` header.
- Requests authenticated by `Authorization: Bearer <jwt>` are exempt:
  cross-origin JS cannot set arbitrary headers on a cross-origin cookied
  request, and bearer tokens are not auto-attached by the browser.

Apply via FastAPI dependency:
    @router.post(..., dependencies=[Depends(csrf_protect)])
or register globally via middleware (see `main.py`).
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import security_logger

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Endpoints that establish or rotate the session itself. These cannot require a
# pre-existing CSRF token because the token is *issued* by these endpoints.
# A stale access cookie from a previous session must not block re-authentication.
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
}


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_protect(request: Request) -> None:
    """Reject mutating requests that authenticate via cookie but lack a valid CSRF header.

    No-op for safe methods, or when the request did not present an access-token cookie
    (i.e. it's authenticating via Authorization header, which is not vulnerable to CSRF).
    """
    if request.method in SAFE_METHODS:
        return

    if request.url.path in CSRF_EXEMPT_PATHS:
        return

    access_cookie = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if not access_cookie:
        # No cookie auth in play -> no CSRF risk.
        return

    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        security_logger.warning(
            "CSRF check failed: missing token (path=%s method=%s)",
            request.url.path,
            request.method,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF token",
        )

    if not secrets.compare_digest(cookie_token, header_token):
        security_logger.warning(
            "CSRF check failed: token mismatch (path=%s method=%s)",
            request.url.path,
            request.method,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )
