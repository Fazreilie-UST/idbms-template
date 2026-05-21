from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.db.deps import get_db
from app.models.auth.user import User
from app.models.build.family import Family
from app.models.build.form_factor import FormFactor
from app.schemas.order.build_request import (
    BuildRequestListResponse,
    BuildRequestResponse,
    BuildRequestRevisionResponse,
)
from app.services import build_request_service


router = APIRouter(prefix="/build-requests", tags=["Build Requests"])


@router.get("", response_model=BuildRequestListResponse)
def list_build_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    family: Optional[str] = None,
    form_factor: Optional[str] = None,
    requestor: Optional[str] = None,
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query(None, pattern="^(asc|desc)$"),
    my_orders: bool = Query(False),
    my_plans: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("build_request:read")),
):
    return build_request_service.list_build_requests(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        family=family,
        form_factor=form_factor,
        requestor=requestor,
        sort_by=sort_by,
        sort_order=sort_order,
        my_orders=my_orders,
        my_plans=my_plans,
        current_user_id=current_user.id,
    )


@router.get("/filter-options")
def get_filter_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_request:read")),
):
    """Distinct filter values (family codes, form factor names, requestors,
    statuses) used to populate dropdown filters in the Build Request Tracker.
    """
    from app.models.order.build_request import BuildRequest

    families = [
        r[0]
        for r in db.query(Family.code).order_by(Family.code.asc()).all()
        if r[0]
    ]
    form_factors = [
        r[0]
        for r in db.query(FormFactor.name).order_by(FormFactor.name.asc()).all()
        if r[0]
    ]
    requestor_rows = (
        db.query(User.id, User.full_name, User.email)
        .join(BuildRequest, BuildRequest.requestor_id == User.id)
        .distinct()
        .order_by(User.full_name.asc())
        .all()
    )
    requestors = [
        {
            "id": r[0],
            "full_name": r[1],
            "email": r[2],
            "label": r[1] or r[2] or f"User #{r[0]}",
        }
        for r in requestor_rows
    ]
    status_rows = (
        db.query(BuildRequest.status).distinct().all()
    )
    statuses = sorted({
        (s[0].value if hasattr(s[0], "value") else str(s[0]))
        for s in status_rows
        if s[0] is not None
    })
    return {
        "families": families,
        "form_factors": form_factors,
        "requestors": requestors,
        "statuses": statuses,
    }


@router.get("/{order_id}", response_model=BuildRequestResponse)
def get_build_request(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_request:read")),
):
    result = build_request_service.get_build_request(db, order_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Build request not found")
    return result


@router.get(
    "/{order_id}/revisions",
    response_model=list[BuildRequestRevisionResponse],
)
def get_build_request_revisions(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_request:read")),
):
    chain = build_request_service.get_revisions_chain(db, order_id)
    if chain is None:
        raise HTTPException(status_code=404, detail="Build request not found")
    return chain
