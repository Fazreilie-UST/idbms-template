from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class FactFinancialValueOut(BaseModel):
    stock_id: int
    metric_id: int
    statement_id: int
    date_id: int
    value: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)