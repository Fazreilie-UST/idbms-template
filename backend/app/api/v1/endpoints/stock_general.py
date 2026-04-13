from fastapi import APIRouter
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.models.stock.import_job import ImportJob
from app.api.v1.endpoints.stock import master, metrics, dates, explorer, facts, statements, imports
from app.db import get_db

router = APIRouter(prefix="/stocks", tags=["stocks"])

router.include_router(master.router)
router.include_router(statements.router)
router.include_router(metrics.router)
router.include_router(dates.router)
router.include_router(facts.router)
router.include_router(explorer.router)
router.include_router(imports.router)