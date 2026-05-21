from typing import Optional
from pydantic import BaseModel


class UserMini(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class BuildRequestResponse(BaseModel):
    id: int
    requestor_id: int
    requestor: Optional[UserMini] = None
    family_code: Optional[str] = None
    form_factor: Optional[str] = None
    config_number: Optional[str] = None
    quantity: int
    status: str
    revision: int
    previous_build_request_id: Optional[int] = None

    model_config = {"from_attributes": True}


class BuildRequestListResponse(BaseModel):
    data: list[BuildRequestResponse]
    page: int
    page_size: int
    total: int


class BuildRequestRevisionResponse(BaseModel):
    """Single revision in the chain."""
    id: int
    revision: int
    status: str
    quantity: int
    requestor: Optional[UserMini] = None
    previous_build_request_id: Optional[int] = None
