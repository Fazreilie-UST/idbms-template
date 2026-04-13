from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.schemas.stock import (
    StockStatementExplorerResponse,
    StockStatementExplorerRequest,
)

from app.services.stock.stock_statement_explorer_service import StockStatementExplorerService


from app.db import get_db

router = APIRouter(prefix="/explorer")

@router.post("/preview", response_model=StockStatementExplorerResponse)
def preview_stock_statement_explorer(
    payload: StockStatementExplorerRequest,
    db: Session = Depends(get_db),
):
    return StockStatementExplorerService(db).preview(payload)