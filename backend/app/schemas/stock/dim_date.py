from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DimDateOut(BaseModel):
    date_id: int
    full_date: date
    year: Optional[int] = None
    month: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)