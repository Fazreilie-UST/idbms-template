from datetime import date
from typing import Optional
from pydantic import BaseModel


class UserMini(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    model_config = {"from_attributes": True}


class ShippingResponse(BaseModel):
    id: int
    config_number: Optional[str] = None
    tracking_number: Optional[str] = None
    forwarder: Optional[str] = None
    quantity: Optional[int] = None
    comments: Optional[str] = None
    ship_date: Optional[date] = None
    eta: Optional[date] = None
    delivery_date: Optional[date] = None
    status: str
    recipient_user: Optional[UserMini] = None
    recipients: list[UserMini] = []


class ShippingListResponse(BaseModel):
    data: list[ShippingResponse]
    page: int
    page_size: int
    total: int
