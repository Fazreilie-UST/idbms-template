from fastapi import APIRouter
from fastapi import Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.schemas.stock import (
    PaginatedResponse,
    DimStockOut,
    ImportResultResponse,
)

from app.services.stock.stock_service import StockService
from app.services.stock.dimension_import_service import DimensionImportService

from app.models.auth.user import User
from app.core.dependencies import get_current_user

from app.db import get_db

router = APIRouter(prefix="/master")

@router.get("/", response_model=PaginatedResponse[DimStockOut])
def get_stock_master(
    skip: int = 0,
    limit: int = Query(100, le=500),
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
):
    return StockService(db).get_stock_master(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.post("/import-csv", response_model=ImportResultResponse)
async def import_dim_stock_csv(
    file: UploadFile = File(...),
    dry_run: str = Form("false"),
    replace_all: str = Form("false"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dry_run_bool = str(dry_run).lower() in ("true", "1", "yes", "on")
    replace_all_bool = str(replace_all).lower() in ("true", "1", "yes", "on")
    return await DimensionImportService(db).import_csv(
        table_name="dim_stock",
        file=file,
        dry_run=dry_run_bool,
        replace_all=replace_all_bool,
        imported_by_id=current_user.id,
    )