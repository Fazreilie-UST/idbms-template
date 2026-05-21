"""Build Request service — query/serialization logic for build_requests endpoints.

Extracted from `app/api/v1/endpoints/build_requests.py` to keep route handlers
thin. Behavior is intentionally unchanged: response shapes and query semantics
match the original endpoint exactly.
"""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.auth.user import User
from app.models.build.build_plan import BuildPlan
from app.models.build.build_plan_access import AccessTypeEnum, BuildPlanAccess
from app.models.build.build_plan_access_override import BuildPlanAccessOverride
from app.models.build.build_plan_build_request import BuildPlanBuildRequest
from app.models.build.config_number import ConfigNumber
from app.models.build.family import Family
from app.models.build.family_form_factor import FamilyFormFactor
from app.models.build.form_factor import FormFactor  # noqa: F401  (used via joinedload chain)
from app.models.order.build_request import BuildRequest
from app.schemas.order.build_request import (
    BuildRequestListResponse,
    BuildRequestResponse,
    BuildRequestRevisionResponse,
    UserMini,
)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _user_mini(user: Optional[User]) -> Optional[UserMini]:
    if not user:
        return None
    return UserMini(id=user.id, full_name=user.full_name, email=user.email)


def _serialize(o: BuildRequest) -> BuildRequestResponse:
    family_code = None
    form_factor = None
    fs = getattr(o, "_family_form_factor", None)
    if o.family_form_factor_id and fs is not None:
        if fs.family:
            family_code = fs.family.code
        if fs.form_factor:
            form_factor = fs.form_factor.name

    return BuildRequestResponse(
        id=o.id,
        requestor_id=o.requestor_id,
        requestor=_user_mini(getattr(o, "requestor", None)),
        family_code=family_code,
        form_factor=form_factor,
        config_number=o.config_number.value if o.config_number else None,
        quantity=o.quantity,
        status=o.status.value if hasattr(o.status, "value") else str(o.status),
        revision=o.revision,
        previous_build_request_id=o.previous_build_request_id,
    )


def _attach_family_form_factor(rows: Iterable[BuildRequest], db: Session) -> None:
    fs_ids = {r.family_form_factor_id for r in rows if r.family_form_factor_id}
    if not fs_ids:
        return
    fs_rows = (
        db.query(FamilyFormFactor)
        .options(joinedload(FamilyFormFactor.family), joinedload(FamilyFormFactor.form_factor))
        .filter(FamilyFormFactor.id.in_(fs_ids))
        .all()
    )
    fs_map = {fs.id: fs for fs in fs_rows}
    for r in rows:
        r._family_form_factor = fs_map.get(r.family_form_factor_id)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

_SORT_COLUMN_MAP = {
    "id": BuildRequest.id,
    "status": BuildRequest.status,
    "quantity": BuildRequest.quantity,
    "revision": BuildRequest.revision,
    "requestor_id": BuildRequest.requestor_id,
}


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def list_build_requests(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: Optional[str],
    status: Optional[str],
    family: Optional[str] = None,
    form_factor: Optional[str] = None,
    requestor: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    my_orders: bool,
    my_plans: bool,
    current_user_id: int,
) -> BuildRequestListResponse:
    """Paginated list with optional search/sort/filter."""
    q = (
        db.query(BuildRequest)
        .options(
            joinedload(BuildRequest.config_number),
            joinedload(BuildRequest.requestor),
        )
    )

    # Join family/form_factor lookup for filter/sort if needed.
    fs_joined = False
    family_joined = False
    ff_joined = False
    requestor_joined = False
    cfg_joined = False

    def _ensure_fs():
        nonlocal q, fs_joined
        if not fs_joined:
            q = q.outerjoin(
                FamilyFormFactor,
                FamilyFormFactor.id == BuildRequest.family_form_factor_id,
            )
            fs_joined = True

    def _ensure_family():
        nonlocal q, family_joined
        _ensure_fs()
        if not family_joined:
            q = q.outerjoin(Family, Family.id == FamilyFormFactor.family_id)
            family_joined = True

    def _ensure_form_factor():
        nonlocal q, ff_joined
        _ensure_fs()
        if not ff_joined:
            q = q.outerjoin(FormFactor, FormFactor.id == FamilyFormFactor.form_factor_id)
            ff_joined = True

    def _ensure_requestor():
        nonlocal q, requestor_joined
        if not requestor_joined:
            q = q.outerjoin(User, User.id == BuildRequest.requestor_id)
            requestor_joined = True

    def _ensure_cfg():
        nonlocal q, cfg_joined
        if not cfg_joined:
            q = q.outerjoin(ConfigNumber, BuildRequest.config_number_id == ConfigNumber.id)
            cfg_joined = True

    if my_orders:
        q = q.filter(BuildRequest.requestor_id == current_user_id)

    if my_plans:
        # Restrict to build requests linked to a build plan the user manages
        # — either via family/FormFactor-level access or a per-build-plan override.
        family_owned_subq = (
            db.query(BuildPlanAccess.family_form_factor_id)
            .filter(
                BuildPlanAccess.user_id == current_user_id,
                BuildPlanAccess.access_type.in_(
                    [AccessTypeEnum.owner, AccessTypeEnum.editor]
                ),
            )
            .subquery()
        )
        plan_owned_subq = (
            db.query(BuildPlanAccessOverride.build_plan_id)
            .filter(
                BuildPlanAccessOverride.user_id == current_user_id,
                BuildPlanAccessOverride.access_type.in_(
                    [AccessTypeEnum.owner, AccessTypeEnum.editor]
                ),
            )
            .subquery()
        )
        # An build request "matches" if it has any linked build plan that the
        # user owns either at family or plan level.
        owned_plans_subq = (
            db.query(BuildPlanBuildRequest.build_request_id)
            .join(BuildPlan, BuildPlan.id == BuildPlanBuildRequest.build_plan_id)
            .filter(
                or_(
                    BuildPlan.family_form_factor_id.in_(family_owned_subq),
                    BuildPlan.id.in_(plan_owned_subq),
                )
            )
            .subquery()
        )
        q = q.filter(BuildRequest.id.in_(owned_plans_subq))

    if status:
        statuses = _split_csv(status)
        if statuses:
            q = q.filter(BuildRequest.status.in_(statuses))

    if family:
        families = _split_csv(family)
        if families:
            _ensure_family()
            q = q.filter(Family.code.in_(families))

    if form_factor:
        ffs = _split_csv(form_factor)
        if ffs:
            _ensure_form_factor()
            q = q.filter(FormFactor.name.in_(ffs))

    if requestor:
        # Match by user id (csv) or by full_name/email (case-insensitive).
        tokens = _split_csv(requestor)
        if tokens:
            _ensure_requestor()
            id_ints: list[int] = []
            name_tokens: list[str] = []
            for t in tokens:
                if t.isdigit():
                    id_ints.append(int(t))
                else:
                    name_tokens.append(t)
            conds = []
            if id_ints:
                conds.append(BuildRequest.requestor_id.in_(id_ints))
            for nt in name_tokens:
                like = f"%{nt}%"
                conds.append(User.full_name.ilike(like))
                conds.append(User.email.ilike(like))
            if conds:
                q = q.filter(or_(*conds))

    if search:
        like = f"%{search}%"
        _ensure_cfg()
        _ensure_requestor()
        _ensure_family()
        _ensure_form_factor()
        q = q.filter(
            or_(
                ConfigNumber.value.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
                Family.code.ilike(like),
                Family.name.ilike(like),
                FormFactor.name.ilike(like),
            )
        )

    total = q.count()

    # Sorting
    sort_key = (sort_by or "id").lower()
    sort_col = _SORT_COLUMN_MAP.get(sort_key, BuildRequest.id)
    extra_order: list = []
    if sort_key == "family":
        _ensure_family()
        sort_col = Family.code
    elif sort_key in ("form_factor", "formfactor"):
        _ensure_form_factor()
        sort_col = FormFactor.name
    elif sort_key == "requestor":
        _ensure_requestor()
        sort_col = User.full_name
    elif sort_key == "config_number":
        _ensure_cfg()
        sort_col = ConfigNumber.value
    elif sort_key == "build_plan_recency":
        # Order by latest linked build plan's (year, work_week) — used by
        # the PM dashboard "Recent Build Requests" tile.
        year_subq = (
            select(func.max(BuildPlan.year))
            .select_from(BuildPlanBuildRequest)
            .join(BuildPlan, BuildPlan.id == BuildPlanBuildRequest.build_plan_id)
            .where(BuildPlanBuildRequest.build_request_id == BuildRequest.id)
            .correlate(BuildRequest)
            .scalar_subquery()
        )
        ww_subq = (
            select(func.max(BuildPlan.work_week))
            .select_from(BuildPlanBuildRequest)
            .join(BuildPlan, BuildPlan.id == BuildPlanBuildRequest.build_plan_id)
            .where(
                BuildPlanBuildRequest.build_request_id == BuildRequest.id,
                BuildPlan.year == year_subq,
            )
            .correlate(BuildRequest)
            .scalar_subquery()
        )
        sort_col = year_subq
        extra_order.append(ww_subq.desc() if (sort_order or "desc").lower() != "asc" else ww_subq.asc())

    desc = (sort_order or "desc").lower() != "asc"
    order_clause = sort_col.desc() if desc else sort_col.asc()
    # Stable secondary order
    rows = (
        q.order_by(order_clause, *extra_order, BuildRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    _attach_family_form_factor(rows, db)

    return BuildRequestListResponse(
        data=[_serialize(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_build_request(db: Session, order_id: int) -> Optional[BuildRequestResponse]:
    o = (
        db.query(BuildRequest)
        .options(
            joinedload(BuildRequest.config_number),
            joinedload(BuildRequest.requestor),
        )
        .filter(BuildRequest.id == order_id)
        .first()
    )
    if not o:
        return None

    _attach_family_form_factor([o], db)
    return _serialize(o)


def get_revisions_chain(
    db: Session, order_id: int
) -> Optional[list[BuildRequestRevisionResponse]]:
    """Return all revisions in the chain (oldest -> newest), based on
    ``previous_build_request_id`` linkage.
    """
    target = (
        db.query(BuildRequest).filter(BuildRequest.id == order_id).first()
    )
    if not target:
        return None

    chain: list[BuildRequest] = [target]
    visited: set[int] = {target.id}

    # Walk backward to root.
    cursor = target
    while (
        cursor.previous_build_request_id
        and cursor.previous_build_request_id not in visited
    ):
        prev = (
            db.query(BuildRequest)
            .filter(BuildRequest.id == cursor.previous_build_request_id)
            .first()
        )
        if not prev:
            break
        chain.append(prev)
        visited.add(prev.id)
        cursor = prev

    # Walk forward — find any orders that point back to current ones.
    forward_cursor_ids: set[int] = {target.id}
    while True:
        children = (
            db.query(BuildRequest)
            .filter(BuildRequest.previous_build_request_id.in_(forward_cursor_ids))
            .all()
        )
        new_ids = {c.id for c in children if c.id not in visited}
        if not new_ids:
            break
        for c in children:
            if c.id in new_ids:
                chain.append(c)
                visited.add(c.id)
        forward_cursor_ids = new_ids

    chain.sort(key=lambda r: (r.revision or 0, r.id))

    user_ids = {r.requestor_id for r in chain if r.requestor_id}
    user_map: dict[int, User] = {}
    if user_ids:
        user_map = {
            u.id: u
            for u in db.query(User).filter(User.id.in_(user_ids)).all()
        }

    return [
        BuildRequestRevisionResponse(
            id=r.id,
            revision=r.revision,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            quantity=r.quantity,
            requestor=_user_mini(user_map.get(r.requestor_id)),
            previous_build_request_id=r.previous_build_request_id,
        )
        for r in chain
    ]
