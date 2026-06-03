from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
    rate_limit_exception_handler,
)

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.csrf import csrf_protect
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.request_limits import MaxBodySizeMiddleware
from app.core.audit_context import AuditContextMiddleware
from app.db.session import SessionLocal
from app.db.audit_listeners import register_audit_listeners
from app.core.logging import setup_logging
from app.core.rate_limit import limiter

# Attach SQLAlchemy session listeners that populate `audit_logs` for every
# CRUD on the audited models. Idempotent; safe under uvicorn --reload.
register_audit_listeners()


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     if settings.ENV == "dev":
#         db = SessionLocal()
#         try:
#             seed_db(db)
#         finally:
#             db.close()
#     yield

setup_logging()


app = FastAPI(
    title="NPI DBMS API",
    # lifespan=lifespan,
)

import os

# Serve bug report attachments from db/bug-report-attachment
bug_report_attachments_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../db/bug-report-attachment"))
app.mount("/db/bug-report-attachment", StaticFiles(directory=bug_report_attachments_dir), name="bug-report-attachments")

app.state.limiter = limiter
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.MAX_REQUEST_BODY_BYTES)
# AuditContextMiddleware must wrap the route handlers so the ContextVars are
# set before any DB session is opened by `get_db`. Adding it last means it
# becomes the outermost middleware in Starlette's stack.
app.add_middleware(AuditContextMiddleware)


def _allowed_origins() -> list[str]:
    origins = [settings.FRONTEND_URL]
    extra = (settings.CORS_EXTRA_ORIGINS or "").strip()
    if extra:
        origins.extend(o.strip() for o in extra.split(",") if o.strip())
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        settings.CSRF_HEADER_NAME,
    ],
    expose_headers=[settings.CSRF_HEADER_NAME],
)

# Apply CSRF protection globally. Safe methods (GET/HEAD/OPTIONS) and
# requests without an access-token cookie are no-ops; see app/core/csrf.py.
app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(csrf_protect)])

# Serve user-uploaded profile pictures. Files are written by the
# /users/me/avatar endpoint to PROFILE_PICTURE_DIR. They are publicly
# readable by URL (the filenames are random hex strings so they are
# unguessable for users who haven't shared them).
_profile_dir = Path(settings.PROFILE_PICTURE_DIR).expanduser()
_profile_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.PROFILE_PICTURE_URL_PREFIX,
    StaticFiles(directory=str(_profile_dir)),
    name="profile-pictures",
)

# Serve documentation assets (screenshots/images embedded in markdown docs).
# Stored in the project repo under `docs/assets/` so updates can be committed
# to version control.
_docs_assets_dir = (
    Path(settings.DOCS_DIR).expanduser() / settings.DOCS_ASSETS_SUBDIR
)
_docs_assets_dir.mkdir(parents=True, exist_ok=True)
(_docs_assets_dir / "screenshots").mkdir(parents=True, exist_ok=True)
app.mount(
    settings.DOCS_ASSETS_URL_PREFIX,
    StaticFiles(directory=str(_docs_assets_dir)),
    name="docs-assets",
)


@app.get("/")
def root():
    return {"message": "FastAPI running"}