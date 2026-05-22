"""Standard security headers middleware.

Applied globally in `main.py`. Headers chosen to be safe for an SPA + JSON API:
- `X-Content-Type-Options: nosniff`           prevents MIME-sniffing
- `X-Frame-Options: DENY`                     blocks framing/clickjacking
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`                        denies sensors/mic/camera/geo by default
- `Cross-Origin-Opener-Policy: same-origin`   process isolation
- `Cross-Origin-Resource-Policy: same-site`   no embedding from other sites
- `Strict-Transport-Security`                 prod-only, expects TLS termination
- `Content-Security-Policy`                   conservative; tighten further once
                                              external image/font hosts are known
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
}

# CSP for a JSON API. The SPA is served separately; tighten origins via env if needed.
_BASE_CSP = (
    "default-src 'none'; "
    "frame-ancestors 'self'; "
    "base-uri 'none'"
)

# Swagger UI / ReDoc are served by FastAPI from a CDN (jsdelivr by default).
# They need a relaxed CSP that allows their script, style, image, and font
# origins, plus inline init script and the favicon data URI.

# Allow embedding docs in iframe from self and localhost:5173 (frontend dev server)
_DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'self' http://localhost:5173; "
    "base-uri 'none'"
)

_DOCS_PATHS = ("/docs", "/redoc", "/docs/oauth2-redirect")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for k, v in _BASE_HEADERS.items():
            response.headers.setdefault(k, v)
        path = request.url.path
        csp = _DOCS_CSP if path in _DOCS_PATHS else _BASE_CSP
        response.headers.setdefault("Content-Security-Policy", csp)
        if settings.ENV == "prod":
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains",
            )
        return response
