import os
os.environ.setdefault("SECRET_KEY", "test-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FRONTEND_URL", "http://localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

print("Step 1: import services")
from app.services import build_plan_service, build_request_service  # noqa: F401
from app.repositories.base import BaseRepository  # noqa: F401
print("  SERVICES_OK")

print("Step 2: import FastAPI app")
from app.main import app
print("  APP_OK routes=" + str(len(app.routes)))

print("Step 3: list routes containing 'health' or 'build-requests' or 'build-plans'")
for r in app.routes:
    p = getattr(r, "path", "")
    if any(k in p for k in ("/health", "/build-requests", "/build-plans")):
        methods = ",".join(sorted(getattr(r, "methods", []) or []))
        print(f"  {methods:10s} {p}")
print("DONE")
