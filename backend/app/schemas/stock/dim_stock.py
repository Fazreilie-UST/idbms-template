from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DimStockOut(BaseModel):
    stock_id: int
    stock_code: str
    stock_number: Optional[str] = None
    stock_name: Optional[str] = None
    weblink: Optional[str] = None
    price: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)