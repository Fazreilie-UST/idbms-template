"""Liveness/readiness endpoints for monitoring and load-balancer probes."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Lightweight liveness probe. Returns 200 OK if the process is up."""
    return {"status": "ok"}
