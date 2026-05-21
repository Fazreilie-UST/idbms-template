"""Reject oversized request bodies before they reach a route handler.

Uploads use ``UploadFile`` which streams to a temp file, so a multi-GB POST
would still hit disk before our route's hash-and-cap check rejects it. This
middleware short-circuits at the framework boundary using the ``Content-Length``
header (best-effort: a missing header falls through to per-route handling).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body exceeds maximum allowed size "
                                      f"of {self.max_bytes} bytes."
                        },
                    )
            except ValueError:
                # Malformed Content-Length: let downstream handle
                pass
        return await call_next(request)
