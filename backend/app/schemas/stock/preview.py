from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class FactPreviewOut(BaseModel):
    stock_id: int
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    metric_name: Optional[str] = None
    statement_name: Optional[str] = None
    full_date: Optional[date] = None
    value: Optional[Decimal] = None