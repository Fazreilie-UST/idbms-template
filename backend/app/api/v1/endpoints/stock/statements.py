from fastapi import APIRouter
from fastapi import Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.schemas.stock import (
    PaginatedResponse,
    ImportResultResponse,
    DimStatementOut,
)

from app.services.stock.stock_service import StockService
from app.services.stock.dimension_import_service import DimensionImportService

from app.models.auth.user import User
from app.core.dependencies import get_current_user

from app.db import get_db

router = APIRouter(prefix="/statements")

@router.get("/", response_model=PaginatedResponse[DimStatementOut])
def get_statements(
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    return StockService(db).get_statements(skip=skip, limit=limit)


@router.post("/import-csv", response_model=ImportResultResponse)
async def import_dim_statement_csv(
    file: UploadFile = File(...),
    dry_run: str = Form("false"),
    replace_all: str = Form("false"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dry_run_bool = str(dry_run).lower() in ("true", "1", "yes", "on")
    replace_all_bool = str(replace_all).lower() in ("true", "1", "yes", "on")
    return await DimensionImportService(db).import_csv(
        table_name="dim_statement",
        file=file,
        dry_run=dry_run_bool,
        replace_all=replace_all_bool,
        imported_by_id=current_user.id,
    )