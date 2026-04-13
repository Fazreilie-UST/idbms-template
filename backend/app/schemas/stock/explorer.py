from typing import Any
from pydantic import BaseModel


class StockStatementExplorerRequest(BaseModel):
    stock_id: int
    statement_id: int


class StockStatementExplorerResponse(BaseModel):
    summary: dict[str, Any]
    rows: list[dict[str, Any]]