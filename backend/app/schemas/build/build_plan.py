from datetime import date
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class BuildPlanSortBy(str, Enum):
    id = "id"
    build_plan_id = "build_plan_id"
    config_number = "config_number"
    support_activity = "support_activity"
    build_description = "build_description"
    build_notes = "build_notes"
    status = "status"
    product_code = "product_code"
    mm_number = "mm_number"
    ta_number = "ta_number"
    pba_number = "pba_number"
    as_number = "as_number"
    revision = "revision"
    build_start_date = "build_start_date"
    ship_date = "ship_date"
    required_quantity = "required_quantity"
    estimated_yield = "estimated_yield"
    family_code = "family_code"
    form_factor = "form_factor"
    year = "year"
    work_week = "work_week"


class BuildPlanListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    search: Optional[str] = None

    family_code: Optional[str] = None
    form_factor: Optional[str] = None
    status: Optional[str] = None
    support_activity: Optional[str] = None

    config_number: Optional[str] = None
    build_description: Optional[str] = None
    build_notes: Optional[str] = None
    year: Optional[str] = None
    silicon_stepping: Optional[str] = None
    product_code: Optional[str] = None
    mm_number: Optional[str] = None
    ta_number: Optional[str] = None
    pba_number: Optional[str] = None
    as_number: Optional[str] = None

    # When set, restrict the result set to imported (True) or web-created
    # (False) build plans. None = no filtering on import origin.
    is_imported: Optional[bool] = None

    sort_by: str = BuildPlanSortBy.id.value
    sort_order: str = SortOrder.desc.value
    my_plans: bool = False
    # When True together with my_plans, restrict to plans where the user is
    # an owner (used for the dashboard "My Build Plans" tile). When False,
    # my_plans includes any explicit access (owner OR editor).
    owner_only: bool = False


class ComponentAttributeResponse(BaseModel):
    name: str
    value: Optional[str] = None


class BuildPlanComponentResponse(BaseModel):
    component_name: str
    component_slot: Optional[str] = None
    supplier: Optional[str] = None
    attributes: list[ComponentAttributeResponse] = []


class BuildPlanTestResponse(BaseModel):
    test_name: str
    test_detail: Optional[str] = None


class UserMini(BaseModel):
    id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


class BuildRequestResponse(BaseModel):
    build_request_id: int
    requestor_name: Optional[str] = None
    quantity: Optional[int] = None


class RecipientRequestorResponse(BaseModel):
    """One requestor inside a recipient block."""
    name: Optional[str] = None
    user_id: Optional[int] = None
    quantity: Optional[int] = None


class BuildPlanRecipientBlock(BaseModel):
    """All requestors that ship through a single recipient user.

    Shape matches the new schema: ``{recipient: ..., requestors: [...]}``.
    """
    recipient: Optional[UserMini] = None
    requestors: list[RecipientRequestorResponse] = []


class WarehouseResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    quantity_stored: int


class ShipmentRecipientResponse(BaseModel):
    """One requestor linked to a shipment via the build plan's SUM-parsed
    handler/recipient mapping (``build_plan_shippings``)."""
    name: Optional[str] = None
    user_id: Optional[int] = None
    quantity: Optional[int] = None


class ShipmentResponse(BaseModel):
    shipment_id: int
    config_number: Optional[str] = None
    tracking_number: Optional[str] = None
    forwarder: Optional[str] = None
    quantity: Optional[int] = None
    comments: Optional[str] = None
    ship_date: Optional[date] = None
    eta: Optional[date] = None
    delivery_date: Optional[date] = None
    status: Optional[str] = None
    recipient_user: Optional[UserMini] = None
    handler_name: Optional[str] = None
    recipients: list[ShipmentRecipientResponse] = []


class BuildPlanResponse(BaseModel):
    model_config = {
        "from_attributes": True
    }

    build_plan_id: int

    family_code: Optional[str] = None
    form_factor: Optional[str] = None

    support_activity: Optional[str] = None
    status: Optional[str] = None

    build_description: Optional[str] = None
    build_notes: list[str] = Field(default_factory=list)

    config_number: Optional[str] = None
    revision: Optional[int] = None

    product_code: Optional[str] = None
    mm_number: Optional[str] = None
    ta_number: Optional[str] = None
    pba_number: Optional[str] = None
    as_number: Optional[str] = None

    special_instruction: Optional[str] = None
    build_start_date: Optional[date] = None
    ship_date: Optional[date] = None

    required_quantity: Optional[int] = None
    estimated_yield: Optional[int] = None

    year: Optional[int] = None
    silicon_steppings: list[str] = Field(default_factory=list)

    # True when this build plan originated from an Excel build-plan import
    # file. Drives the "Imported" UI tag.
    is_imported: bool = False

    components: list[BuildPlanComponentResponse] = []
    tests: list[BuildPlanTestResponse] = []
    build_requests: list[BuildRequestResponse] = []
    recipients: list[BuildPlanRecipientBlock] = []
    warehouses: list[WarehouseResponse] = []
    shipments: list[ShipmentResponse] = []


class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class SortingResponse(BaseModel):
    sort_by: str
    sort_order: str


class BuildPlanListResponse(BaseModel):
    data: list[BuildPlanResponse]
    pagination: PaginationResponse
    sorting: SortingResponse
    filters: dict[str, Any]


class ManualRevisionCreate(BaseModel):
    """Payload for POST /build-plans/{id}/revisions.

    All fields are optional; only those provided are merged into the new
    revision's snapshot. Child sections (components, tests, build requests,
    warehouse quantities) are NOT editable here in v1 — they are managed via
    re-importing the build plan file.
    """

    status: Optional[str] = None
    support_activity: Optional[str] = None
    build_description: Optional[str] = None

    product_code: Optional[str] = None
    mm_number: Optional[str] = None
    ta_number: Optional[str] = None
    pba_number: Optional[str] = None
    as_number: Optional[str] = None
    special_instruction: Optional[str] = None

    required_quantity: Optional[int] = None
    # Accept either a percent (e.g. 95) or a decimal fraction (e.g. 0.95);
    # the service layer normalises this to an integer percent before storage.
    estimated_yield: Optional[float] = None
    build_start_quantity: Optional[int] = None

    build_notes: Optional[list[str]] = None
