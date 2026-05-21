"""Build Plan endpoints ? thin route handlers delegating to the service layer.

All query/aggregation logic lives in `app.services.build_plan_service`.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.core.rate_limit import limiter
from app.db.deps import get_db
from app.models.auth.user import User
from app.models.build.build_plan import BuildPlan
from app.models.build.build_plan_access import AccessTypeEnum, BuildPlanAccess
from app.models.build.build_plan_access_override import BuildPlanAccessOverride
from app.models.build.build_plan_import_file import BuildPlanImportFile
from app.models.build.build_plan_import_file_touch import BuildPlanImportFileTouch
from app.models.build.build_plan_import_shipping_info import (
    BuildPlanImportShippingInfo,
)
from app.models.build.build_plan_import_si import BuildPlanImportSi
from app.models.build.build_plan_revision import BuildPlanRevision
from app.schemas.build.build_plan import (
    BuildPlanListQuery,
    BuildPlanListResponse,
    BuildPlanSortBy,
    ManualRevisionCreate,
    SortOrder,
)
from app.scripts import seed_build_plan as sbp_helpers
from app.services import build_plan_service
from app.services.build_plan_revision_service import (
    ManualRevisionNoChangeError,
    ManualRevisionNotAllowedError,
    StatusRegressionError,
    create_manual_revision,
)


router = APIRouter(prefix="/build-plans", tags=["Build Plans"])


def get_build_plan_query(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    family_code: str | None = Query(None),
    form_factor: str | None = Query(None),
    status: str | None = Query(None),
    support_activity: str | None = Query(None),
    config_number: str | None = Query(None),
    build_description: str | None = Query(None),
    build_notes: str | None = Query(None),
    product_code: str | None = Query(None),
    mm_number: str | None = Query(None),
    ta_number: str | None = Query(None),
    pba_number: str | None = Query(None),
    as_number: str | None = Query(None),
    year: str | None = Query(None),
    silicon_stepping: str | None = Query(None),
    sort_by: str | None = Query(BuildPlanSortBy.id.value),
    sort_order: str | None = Query(SortOrder.desc.value),
    my_plans: bool = Query(False),
    owner_only: bool = Query(False),
) -> BuildPlanListQuery:
    return BuildPlanListQuery(
        page=page,
        page_size=page_size,
        search=search,
        family_code=family_code,
        form_factor=form_factor,
        status=status,
        support_activity=support_activity,
        config_number=config_number,
        build_description=build_description,
        build_notes=build_notes,
        product_code=product_code,
        mm_number=mm_number,
        ta_number=ta_number,
        pba_number=pba_number,
        as_number=as_number,
        year=year,
        silicon_stepping=silicon_stepping,
        sort_by=sort_by or BuildPlanSortBy.id.value,
        sort_order=sort_order or SortOrder.desc.value,
        my_plans=my_plans,
        owner_only=owner_only,
    )


@router.get("", response_model=BuildPlanListResponse)
@limiter.limit("120/minute")
def get_build_plans(
    request: Request,
    query: BuildPlanListQuery = Depends(get_build_plan_query),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("build_plan:read")),
):
    return build_plan_service.list_build_plans(
        db, query, current_user_id=current_user.id
    )


@router.get("/filter-options")
def get_build_plan_filter_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return build_plan_service.get_filter_options(db)


@router.get("/{build_plan_id}")
def get_build_plan_by_id(
    build_plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    result = build_plan_service.get_build_plan_by_id(db, build_plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Build plan not found")
    return result


@router.get("/{build_plan_id}/revisions")
def get_build_plan_revisions(
    build_plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    result = build_plan_service.get_build_plan_revisions(db, build_plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Build plan not found")
    return result


# ---------------------------------------------------------------------------
# Auxiliary import-sheet data (Shipping Info / Si)
# ---------------------------------------------------------------------------

class ExtraSheetFileSummary(BaseModel):
    id: int
    original_filename: str
    work_week: int | None = None
    work_year: int | None = None
    file_revision: int | None = None


class ExtraShippingInfoRow(BaseModel):
    id: int
    import_file_id: int
    row_index: int | None = None
    responsibility: str | None = None
    name: str | None = None
    address: str | None = None


class ExtraSiRow(BaseModel):
    id: int
    import_file_id: int
    row_index: int | None = None
    si_description: str | None = None
    si_lot_numbers: str | None = None
    class_test_rev: str | None = None
    request_qty: int | None = None
    request_dock_date: str | None = None
    commit_qty: int | None = None
    commit_dock_date: str | None = None
    actual_qty: int | None = None
    actual_dock_date: str | None = None
    comments: str | None = None


class BuildPlanExtraSheetsResponse(BaseModel):
    build_plan_id: int
    family_form_factor_id: int | None = None
    family_code: str | None = None
    form_factor: str | None = None
    files: list[ExtraSheetFileSummary]
    shipping_infos: list[ExtraShippingInfoRow]
    si_rows: list[ExtraSiRow]


@router.get(
    "/{build_plan_id}/extra-sheets",
    response_model=BuildPlanExtraSheetsResponse,
)
def get_build_plan_extra_sheets(
    build_plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    """Aggregate the *Shipping Info* and *Si* sheet rows captured from every
    import file that touched a build plan sharing this plan's ``family_form_factor``.

    The original sheets are file-level (not per-build-plan), so the link is
    "any file that produced or touched a sibling build plan in the same
    family + FormFactor". Rows are returned with their ``import_file_id`` so the UI
    can group / annotate them.
    """
    plan = (
        db.query(BuildPlan.id, BuildPlan.family_form_factor_id)
        .filter(BuildPlan.id == build_plan_id)
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Build plan not found")

    family_form_factor_id = plan.family_form_factor_id

    # Derive readable family / sku codes (best-effort; the helper service
    # already builds these in get_build_plan_by_id).
    info = build_plan_service.get_build_plan_by_id(db, build_plan_id) or {}
    family_code = info.get("family_code")
    form_factor = info.get("form_factor")

    file_ids: set[int] = set()
    if family_form_factor_id is not None:
        # Use correlated subqueries so we never materialize the full sibling
        # id list (a single family/FormFactor can have hundreds of build plans, each
        # touched by many import files). Two scalar DISTINCT queries scoped
        # to the family_form_factor_id are cheaper than fetch-then-IN.
        sibling_subq = (
            db.query(BuildPlan.id)
            .filter(BuildPlan.family_form_factor_id == family_form_factor_id)
            .subquery()
        )
        rev_file_ids = (
            db.query(BuildPlanRevision.import_file_id)
            .filter(
                BuildPlanRevision.build_plan_id.in_(sibling_subq.select()),
                BuildPlanRevision.import_file_id.isnot(None),
            )
            .distinct()
            .all()
        )
        touch_file_ids = (
            db.query(BuildPlanImportFileTouch.import_file_id)
            .filter(BuildPlanImportFileTouch.build_plan_id.in_(sibling_subq.select()))
            .distinct()
            .all()
        )
        file_ids = {row[0] for row in rev_file_ids if row[0] is not None}
        file_ids.update(row[0] for row in touch_file_ids if row[0] is not None)

    if not file_ids:
        return BuildPlanExtraSheetsResponse(
            build_plan_id=build_plan_id,
            family_form_factor_id=family_form_factor_id,
            family_code=family_code,
            form_factor=form_factor,
            files=[],
            shipping_infos=[],
            si_rows=[],
        )

    files = (
        db.query(BuildPlanImportFile)
        .filter(BuildPlanImportFile.id.in_(file_ids))
        .order_by(
            BuildPlanImportFile.work_year.desc().nullslast(),
            BuildPlanImportFile.work_week.desc().nullslast(),
            BuildPlanImportFile.file_revision.desc().nullslast(),
            BuildPlanImportFile.created_at.desc(),
        )
        .all()
    )

    # Hard cap on auxiliary rows. The UI renders these in a modal, so we
    # never want to ship 100k+ rows in one response. The cap is generous
    # enough to be invisible in normal use (most families have at most a few
    # hundred rows total across all import files).
    _EXTRA_SHEETS_ROW_CAP = 10_000

    shipping_rows = (
        db.query(BuildPlanImportShippingInfo)
        .filter(BuildPlanImportShippingInfo.import_file_id.in_(file_ids))
        .order_by(
            BuildPlanImportShippingInfo.import_file_id.asc(),
            BuildPlanImportShippingInfo.row_index.asc().nullslast(),
            BuildPlanImportShippingInfo.id.asc(),
        )
        .limit(_EXTRA_SHEETS_ROW_CAP)
        .all()
    )
    si_rows = (
        db.query(BuildPlanImportSi)
        .filter(BuildPlanImportSi.import_file_id.in_(file_ids))
        .order_by(
            BuildPlanImportSi.import_file_id.asc(),
            BuildPlanImportSi.row_index.asc().nullslast(),
            BuildPlanImportSi.id.asc(),
        )
        .limit(_EXTRA_SHEETS_ROW_CAP)
        .all()
    )

    return BuildPlanExtraSheetsResponse(
        build_plan_id=build_plan_id,
        family_form_factor_id=family_form_factor_id,
        family_code=family_code,
        form_factor=form_factor,
        files=[
            ExtraSheetFileSummary(
                id=f.id,
                original_filename=f.original_filename,
                work_week=f.work_week,
                work_year=f.work_year,
                file_revision=f.file_revision,
            )
            for f in files
        ],
        shipping_infos=[
            ExtraShippingInfoRow(
                id=r.id,
                import_file_id=r.import_file_id,
                row_index=r.row_index,
                responsibility=r.responsibility,
                name=r.name,
                address=r.address,
            )
            for r in shipping_rows
        ],
        si_rows=[
            ExtraSiRow(
                id=r.id,
                import_file_id=r.import_file_id,
                row_index=r.row_index,
                si_description=r.si_description,
                si_lot_numbers=r.si_lot_numbers,
                class_test_rev=r.class_test_rev,
                request_qty=r.request_qty,
                request_dock_date=r.request_dock_date,
                commit_qty=r.commit_qty,
                commit_dock_date=r.commit_dock_date,
                actual_qty=r.actual_qty,
                actual_dock_date=r.actual_dock_date,
                comments=r.comments,
            )
            for r in si_rows
        ],
    )


@router.post("/{build_plan_id}/revisions", status_code=201)
@limiter.limit("30/minute")
def create_build_plan_revision(
    request: Request,
    build_plan_id: int,
    payload: ManualRevisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("build_plan:revise")),
):
    """Author a manual revision for a build plan.

    Only plan-level scalar fields and status may be edited via this endpoint.
    Child sections (components, tests, build requests, warehouse quantities)
    must be revised by re-importing the build plan file.
    """
    bp = db.query(BuildPlan).filter_by(id=build_plan_id).first()
    if bp is None:
        raise HTTPException(status_code=404, detail="Build plan not found")

    updates = payload.model_dump(exclude_unset=True, exclude_none=False)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No editable fields supplied.",
        )

    try:
        rev = create_manual_revision(
            db,
            build_plan=bp,
            plan_updates=updates,
            seed_helpers=sbp_helpers,
        )
    except ManualRevisionNotAllowedError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except ManualRevisionNoChangeError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except StatusRegressionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(rev)
    return {
        "revision_id": rev.id,
        "revision_number": rev.revision_number,
        "build_plan_id": bp.id,
        "status": rev.status_at_revision.value,
        "changed_fields": rev.changed_fields,
        "created_at": rev.created_at.isoformat() if rev.created_at else None,
    }


# ---------------------------------------------------------------------------
# Build plan access management
# ---------------------------------------------------------------------------

import enum as _enum

from app.services.rbac_service import RBACService

_ACCESS_RANK = {AccessTypeEnum.editor: 1, AccessTypeEnum.owner: 2}


def _is_admin(user: User) -> bool:
    return "Admin" in RBACService.get_user_roles(user)


def _is_plan_owner(db: Session, user_id: int, build_plan_id: int) -> bool:
    """True iff the user owns the build plan at family or plan level."""
    plan_fs = (
        db.query(BuildPlan.family_form_factor_id)
        .filter(BuildPlan.id == build_plan_id)
        .scalar()
    )
    if plan_fs is not None:
        family_owned = (
            db.query(BuildPlanAccess.access_id)
            .filter(
                BuildPlanAccess.family_form_factor_id == plan_fs,
                BuildPlanAccess.user_id == user_id,
                BuildPlanAccess.access_type == AccessTypeEnum.owner,
            )
            .first()
        )
        if family_owned:
            return True
    plan_owned = (
        db.query(BuildPlanAccessOverride.id)
        .filter(
            BuildPlanAccessOverride.build_plan_id == build_plan_id,
            BuildPlanAccessOverride.user_id == user_id,
            BuildPlanAccessOverride.access_type == AccessTypeEnum.owner,
        )
        .first()
    )
    return bool(plan_owned)


def _ensure_can_manage_access(
    db: Session, user: User, build_plan_ids: list[int]
) -> None:
    """Admins can always manage. Otherwise the user must be the owner of
    *every* selected build plan (family- or plan-level)."""
    if _is_admin(user):
        return
    for bp_id in build_plan_ids:
        if not _is_plan_owner(db, user.id, bp_id):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only an admin or an owner of the build plan can manage "
                    "access. You must be the owner of every selected build plan."
                ),
            )


class AccessScope(str, _enum.Enum):
    plan = "plan"
    family = "family"


class AccessUserSummary(BaseModel):
    id: int
    full_name: str | None = None
    email: str | None = None


class AccessEntry(BaseModel):
    user: AccessUserSummary
    access_type: AccessTypeEnum
    scope: AccessScope  # 'family' or 'plan'
    family_form_factor_id: int | None = None


class BuildPlanAccessListResponse(BaseModel):
    build_plan_id: int
    can_manage: bool
    entries: list[AccessEntry]


@router.get("/{build_plan_id}/access", response_model=BuildPlanAccessListResponse)
def list_build_plan_access(
    build_plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("build_plan:read")),
):
    """List all users who have explicit access on a build plan (family-level
    or plan-level override). Implicit viewer access (every authenticated user)
    is not included."""
    bp = (
        db.query(BuildPlan.id, BuildPlan.family_form_factor_id)
        .filter(BuildPlan.id == build_plan_id)
        .first()
    )
    if not bp:
        raise HTTPException(status_code=404, detail="Build plan not found")

    entries: list[AccessEntry] = []

    family_rows = (
        db.query(BuildPlanAccess, User)
        .join(User, User.id == BuildPlanAccess.user_id)
        .filter(BuildPlanAccess.family_form_factor_id == bp.family_form_factor_id)
        .all()
        if bp.family_form_factor_id
        else []
    )
    for row, user in family_rows:
        entries.append(
            AccessEntry(
                user=AccessUserSummary(id=user.id, full_name=user.full_name, email=user.email),
                access_type=row.access_type,
                scope=AccessScope.family,
                family_form_factor_id=row.family_form_factor_id,
            )
        )

    override_rows = (
        db.query(BuildPlanAccessOverride, User)
        .join(User, User.id == BuildPlanAccessOverride.user_id)
        .filter(BuildPlanAccessOverride.build_plan_id == build_plan_id)
        .all()
    )
    for row, user in override_rows:
        entries.append(
            AccessEntry(
                user=AccessUserSummary(id=user.id, full_name=user.full_name, email=user.email),
                access_type=row.access_type,
                scope=AccessScope.plan,
            )
        )

    can_manage = _is_admin(current_user) or _is_plan_owner(db, current_user.id, build_plan_id)

    return BuildPlanAccessListResponse(
        build_plan_id=build_plan_id,
        can_manage=can_manage,
        entries=entries,
    )


class GrantAccessRequest(BaseModel):
    build_plan_ids: list[int] = Field(min_length=1)
    user_ids: list[int] = Field(min_length=1)
    access_type: AccessTypeEnum
    # Default to plan-level (narrow) per UX guidelines: grant only on the
    # specific build plans the PM selected. Use ``family`` to broaden access
    # to every plan sharing the same family/FormFactor.
    scope: AccessScope = AccessScope.plan


class GrantAccessResult(BaseModel):
    scope: AccessScope
    granted: int  # number of access rows created
    upgraded: int  # number of existing rows whose access_type was raised
    unchanged: int  # rows already at or above the requested level
    family_form_factor_ids: list[int] = []
    build_plan_ids: list[int] = []
    missing_build_plan_ids: list[int] = []
    missing_user_ids: list[int] = []


@router.post("/access", response_model=GrantAccessResult)
def grant_build_plan_access(
    payload: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("build_plan:update")),
):
    """Grant editor/owner access on the selected build plans.

    Scope semantics:
      * ``plan`` (default): one ``BuildPlanAccessOverride`` row per
        (build_plan, user). Narrow — only the specific plans selected.
      * ``family``: one ``BuildPlanAccess`` row per (family_form_factor, user). Broad
        — every plan that shares the same family/FormFactor is implicitly covered.

    Access is *raise-only*: if an existing row already has equal or higher
    access, it is left untouched (reported under ``unchanged``).
    """
    _ensure_can_manage_access(db, current_user, payload.build_plan_ids)

    plans = (
        db.query(BuildPlan.id, BuildPlan.family_form_factor_id)
        .filter(BuildPlan.id.in_(payload.build_plan_ids))
        .all()
    )
    found_plan_ids = {p.id for p in plans}
    missing_plan_ids = [i for i in payload.build_plan_ids if i not in found_plan_ids]

    found_users = (
        db.query(User.id)
        .filter(User.id.in_(payload.user_ids))
        .all()
    )
    found_user_ids = {u.id for u in found_users}
    missing_user_ids = [i for i in payload.user_ids if i not in found_user_ids]

    target_rank = _ACCESS_RANK[payload.access_type]

    if not found_plan_ids or not found_user_ids:
        return GrantAccessResult(
            scope=payload.scope,
            granted=0,
            upgraded=0,
            unchanged=0,
            missing_build_plan_ids=missing_plan_ids,
            missing_user_ids=missing_user_ids,
        )

    granted = upgraded = unchanged = 0

    if payload.scope == AccessScope.family:
        family_form_factor_ids = sorted({p.family_form_factor_id for p in plans if p.family_form_factor_id})
        existing_rows = (
            db.query(BuildPlanAccess)
            .filter(
                BuildPlanAccess.family_form_factor_id.in_(family_form_factor_ids),
                BuildPlanAccess.user_id.in_(found_user_ids),
            )
            .all()
        )
        existing_index = {(r.family_form_factor_id, r.user_id): r for r in existing_rows}

        for fs_id in family_form_factor_ids:
            for user_id in found_user_ids:
                row = existing_index.get((fs_id, user_id))
                if row is None:
                    db.add(
                        BuildPlanAccess(
                            family_form_factor_id=fs_id,
                            user_id=user_id,
                            access_type=payload.access_type,
                        )
                    )
                    granted += 1
                    continue
                current_rank = _ACCESS_RANK.get(row.access_type, 0)
                if target_rank > current_rank:
                    row.access_type = payload.access_type
                    upgraded += 1
                else:
                    unchanged += 1

        db.commit()
        return GrantAccessResult(
            scope=payload.scope,
            granted=granted,
            upgraded=upgraded,
            unchanged=unchanged,
            family_form_factor_ids=family_form_factor_ids,
            missing_build_plan_ids=missing_plan_ids,
            missing_user_ids=missing_user_ids,
        )

    # scope == plan
    bp_to_fs = {p.id: p.family_form_factor_id for p in plans}
    existing_overrides = (
        db.query(BuildPlanAccessOverride)
        .filter(
            BuildPlanAccessOverride.build_plan_id.in_(found_plan_ids),
            BuildPlanAccessOverride.user_id.in_(found_user_ids),
        )
        .all()
    )
    override_index = {(r.build_plan_id, r.user_id): r for r in existing_overrides}

    # Also consider family-level access that already covers the user: if they
    # already have >= the requested access at the family level for the plan's
    # family_form_factor, a per-plan override is redundant — count it as "unchanged"
    # and skip the insert. Keeps the table from filling up with redundant rows.
    fs_ids = sorted({fs for fs in bp_to_fs.values() if fs})
    family_rows = (
        db.query(BuildPlanAccess)
        .filter(
            BuildPlanAccess.family_form_factor_id.in_(fs_ids),
            BuildPlanAccess.user_id.in_(found_user_ids),
        )
        .all()
        if fs_ids
        else []
    )
    family_index = {(r.family_form_factor_id, r.user_id): r for r in family_rows}

    for plan_id in sorted(found_plan_ids):
        fs_id = bp_to_fs.get(plan_id)
        for user_id in found_user_ids:
            fam_row = family_index.get((fs_id, user_id)) if fs_id else None
            fam_rank = _ACCESS_RANK.get(fam_row.access_type, 0) if fam_row else 0
            if fam_rank >= target_rank:
                unchanged += 1
                continue

            row = override_index.get((plan_id, user_id))
            if row is None:
                db.add(
                    BuildPlanAccessOverride(
                        build_plan_id=plan_id,
                        user_id=user_id,
                        access_type=payload.access_type,
                    )
                )
                granted += 1
                continue
            current_rank = _ACCESS_RANK.get(row.access_type, 0)
            if target_rank > current_rank:
                row.access_type = payload.access_type
                upgraded += 1
            else:
                unchanged += 1

    db.commit()

    return GrantAccessResult(
        scope=payload.scope,
        granted=granted,
        upgraded=upgraded,
        unchanged=unchanged,
        build_plan_ids=sorted(found_plan_ids),
        missing_build_plan_ids=missing_plan_ids,
        missing_user_ids=missing_user_ids,
    )
