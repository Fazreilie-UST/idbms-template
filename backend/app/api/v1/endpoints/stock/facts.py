from fastapi import APIRouter
from fastapi import Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.schemas.stock import (
    PaginatedResponse,
    ImportResultResponse,
    FactFinancialValueOut,
)

from app.services.stock.stock_service import StockService
from app.services.stock.fact_import_service import FinancialFactsImportService

from app.models.auth.user import User
from app.core.dependencies import get_current_user

from app.db import get_db

router = APIRouter(prefix="/facts")

@router.get("/", response_model=PaginatedResponse[FactFinancialValueOut])
def get_facts(
    skip: int = 0,
    limit: int = Query(100, le=500),
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
):
    return StockService(db).get_facts(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    

@router.post("/import-csv", response_model=ImportResultResponse)
async def import_financial_facts_csv(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    replace_all: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    replace_all_bool = str(replace_all).lower() in ("true", "1", "yes", "on")

    return await FinancialFactsImportService(db).import_csv(
        file=file,
        dry_run=dry_run,
        replace_all=replace_all_bool,
        imported_by_id=current_user.id,
    )