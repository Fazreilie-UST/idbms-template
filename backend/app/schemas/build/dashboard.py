"""Pydantic schemas for the Business Overview dashboard.

A single shared filter object is reused by every dashboard endpoint so that
client-side cross-filtering only needs to send one consistent query string.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared filter
# ---------------------------------------------------------------------------

class DashboardFilters(BaseModel):
    """Filters accepted by every business-overview endpoint."""

    year: Optional[int] = Field(None, description="Year of ship_date")
    family_codes: List[str] = Field(default_factory=list)
    form_factors: List[str] = Field(default_factory=list)
    support_activities: List[str] = Field(default_factory=list)
    statuses: List[str] = Field(default_factory=list)
    silicon_steppings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class KpiResponse(BaseModel):
    total_builds: int
    total_boards: float
    total_families: int
    total_form_factors: int
    milestone_builds: int


class CategoryCount(BaseModel):
    label: str
    value: float


class FormFactorValue(BaseModel):
    form_factor: str
    value: float


class FamilyBreakdown(BaseModel):
    family_code: str
    family_name: str
    total: float
    form_factors: List[FormFactorValue]


class FamilyBreakdownResponse(BaseModel):
    metric: str  # "boards" or "builds"
    families: List[FamilyBreakdown]


class StackedBarRow(BaseModel):
    """One stacked-bar data point: (x = support_activity, stack = form_factor, value)."""

    support_activity: str
    form_factor: str
    value: float


class StackedBarResponse(BaseModel):
    metric: str
    rows: List[StackedBarRow]


class ComponentSlotOption(BaseModel):
    component_name: str
    slot_code: Optional[str] = None


class FilterLookupResponse(BaseModel):
    """Distinct values used to populate filter dropdowns."""

    families: List[CategoryCount]
    form_factors: List[CategoryCount]
    support_activities: List[str]
    statuses: List[str]
    silicon_steppings: List[str]
    years: List[int]
    components: List[str] = []
    component_slots: List[ComponentSlotOption] = []


# ---------------------------------------------------------------------------
# Phase 2 — additional responses
# ---------------------------------------------------------------------------

class RequiredQtyRow(BaseModel):
    family_code: str
    form_factor: str
    required_quantity: int


class MilestoneTimelinePoint(BaseModel):
    period: str  # "YYYY-MM"
    count: int


class FamilyComparisonFormFactorRow(BaseModel):
    form_factor: str
    silicon_steppings: List[CategoryCount]
    pcb_revisions: List[CategoryCount]
    total_builds: int
    total_boards: float


class FamilyComparisonResponse(BaseModel):
    family_code: str
    family_name: str
    form_factors: List[FamilyComparisonFormFactorRow]


class FamilyAttributeBreakdown(BaseModel):
    """Per-family breakdown of build-plan attribute distributions: silicon
    stepping, PCB revision and HW revision."""

    family_code: str
    family_name: str
    silicon_steppings: List[CategoryCount]
    pcb_revisions: List[CategoryCount]
    hw_revisions: List[CategoryCount]


class FamilyAttributeBreakdownResponse(BaseModel):
    families: List[FamilyAttributeBreakdown]


# ---------------------------------------------------------------------------
# Supplier × Component breakdown
# ---------------------------------------------------------------------------

class SupplierComponentRow(BaseModel):
    component_slot: str
    supplier: str
    builds: int
    boards: float


class SupplierComponentResponse(BaseModel):
    metric: str          # "builds" or "boards"
    component_name: str
    rows: List[SupplierComponentRow]


class SupplierComponentDetailRow(BaseModel):
    """One row for the detailed (slot × supplier × attributes) breakdown."""

    component_slot: str
    supplier: str
    attributes: Dict[str, Optional[str]] = Field(default_factory=dict)
    builds: int
    boards: float
    required_quantity: int


class SupplierComponentDetailResponse(BaseModel):
    component_name: str
    columns: List[str] = Field(
        default_factory=list,
        description="Ordered list of attribute names that appear in the rows.",
    )
    rows: List[SupplierComponentDetailRow]


class PcbSupplierCountRow(BaseModel):
    """One row of the 'Count by PCB Supplier' breakdown."""

    pcb_supplier: str
    builds: int
    boards: float


class PcbSupplierCountResponse(BaseModel):
    component_name: str
    rows: List[PcbSupplierCountRow]
