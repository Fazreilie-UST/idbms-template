from fastapi import APIRouter

from app.api.v1.endpoints.stock import master, metrics, dates, explorer, facts, statements, imports

router = APIRouter(prefix="/stocks", tags=["stocks"])

router.include_router(master.router)
router.include_router(statements.router)
router.include_router(metrics.router)
router.include_router(dates.router)
router.include_router(facts.router)
router.include_router(explorer.router)
router.include_router(imports.router)