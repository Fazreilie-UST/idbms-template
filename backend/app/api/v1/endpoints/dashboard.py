"""Business Overview dashboard endpoints.

All endpoints share the same query-string filter set so the frontend can wire
cross-filtering trivially: clicking a slice updates one filter, and every
widget re-requests with the same params.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.core.rate_limit import limiter
from app.db.deps import get_db
from app.models.auth.user import User
from app.schemas.build.dashboard import (
    CategoryCount,
    DashboardFilters,
    FamilyAttributeBreakdownResponse,
    FamilyBreakdownResponse,
    FamilyComparisonResponse,
    FilterLookupResponse,
    KpiResponse,
    MilestoneTimelinePoint,
    RequiredQtyRow,
    StackedBarResponse,
    SupplierComponentDetailResponse,
    SupplierComponentResponse,
    PcbSupplierCountResponse,
)
from app.services import dashboard_service


router = APIRouter(prefix="/dashboard/business", tags=["Dashboard"])


def _filters(
    year: Optional[int] = Query(None),
    family_code: List[str] = Query(default_factory=list),
    form_factor: List[str] = Query(default_factory=list),
    support_activity: List[str] = Query(default_factory=list),
    status: List[str] = Query(default_factory=list),
    silicon_stepping: List[str] = Query(default_factory=list),
) -> DashboardFilters:
    return DashboardFilters(
        year=year,
        family_codes=family_code,
        form_factors=form_factor,
        support_activities=support_activity,
        statuses=status,
        silicon_steppings=silicon_stepping,
    )


@router.get("/kpis", response_model=KpiResponse)
@limiter.limit("120/minute")
def get_kpis(
    request: Request,
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_kpis(db, filters)


@router.get("/family-breakdown", response_model=FamilyBreakdownResponse)
@limiter.limit("120/minute")
def get_family_breakdown(
    request: Request,
    metric: str = Query("boards", pattern="^(boards|builds)$"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_family_breakdown(db, filters, metric)


@router.get(
    "/family-attribute-breakdown",
    response_model=FamilyAttributeBreakdownResponse,
)
@limiter.limit("120/minute")
def get_family_attribute_breakdown(
    request: Request,
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_family_attribute_breakdown(db, filters)


@router.get("/support-activity-breakdown", response_model=StackedBarResponse)
@limiter.limit("120/minute")
def get_support_activity_breakdown(
    request: Request,
    metric: str = Query("builds", pattern="^(boards|builds)$"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_support_activity_breakdown(db, filters, metric)


@router.get("/silicon-stepping", response_model=List[CategoryCount])
@limiter.limit("120/minute")
def get_silicon_stepping(
    request: Request,
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_silicon_stepping_breakdown(db, filters)


@router.get("/lookups", response_model=FilterLookupResponse)
@limiter.limit("120/minute")
def get_lookups(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_filter_lookups(db)


# ---------------------------------------------------------------------------
# Phase 2 endpoints
# ---------------------------------------------------------------------------


@router.get("/required-quantity-top", response_model=List[RequiredQtyRow])
@limiter.limit("120/minute")
def get_required_quantity_top(
    request: Request,
    limit: int = Query(15, ge=1, le=50),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_required_quantity_top(db, filters, limit)


@router.get("/milestone-timeline", response_model=List[MilestoneTimelinePoint])
@limiter.limit("120/minute")
def get_milestone_timeline(
    request: Request,
    metric: str = Query("builds", pattern="^(boards|builds)$"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_milestone_timeline(db, filters, metric)


@router.get(
    "/family-comparison/{code}", response_model=FamilyComparisonResponse
)
@limiter.limit("120/minute")
def get_family_comparison(
    request: Request,
    code: str = Path(..., alias="code"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_family_comparison(db, filters, code)


@router.get("/supplier-component", response_model=SupplierComponentResponse)
@limiter.limit("120/minute")
def get_supplier_component(
    request: Request,
    component_name: str = Query(..., description="Component name, e.g. Crystal"),
    metric: str = Query("builds", pattern="^(boards|builds)$"),
    slot_code: Optional[str] = Query(None, description="Filter to a specific slot code"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_supplier_component_breakdown(
        db, filters, component_name, metric, slot_code
    )


@router.get(
    "/supplier-component-detail",
    response_model=SupplierComponentDetailResponse,
)
@limiter.limit("120/minute")
def get_supplier_component_detail(
    request: Request,
    component_name: str = Query(..., description="Component name, e.g. Crystal"),
    slot_code: Optional[str] = Query(None, description="Filter to a specific slot code"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_supplier_component_detail(
        db, filters, component_name, slot_code
    )


@router.get(
    "/supplier-component-by-pcb-supplier",
    response_model=PcbSupplierCountResponse,
)
@limiter.limit("120/minute")
def get_supplier_component_by_pcb_supplier(
    request: Request,
    component_name: str = Query(..., description="Component name, e.g. Crystal"),
    slot_code: Optional[str] = Query(None, description="Filter to a specific slot code"),
    filters: DashboardFilters = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return dashboard_service.get_supplier_component_by_pcb_supplier(
        db, filters, component_name, slot_code
    )



