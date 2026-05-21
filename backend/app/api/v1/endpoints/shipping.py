from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, bindparam, text
from sqlalchemy.orm import Session, joinedload

from app.db.deps import get_db
from app.core.dependencies import require_permission
from app.models.auth.user import User
from app.models.order.shipping import Shipping
from app.models.order.forwarder import Forwarder
from app.models.build.build_plan import BuildPlan
from app.models.build.build_plan_access import AccessTypeEnum, BuildPlanAccess
from app.models.build.build_plan_access_override import BuildPlanAccessOverride
from app.models.build.config_number import ConfigNumber
from app.models.build.family import Family
from app.models.build.family_form_factor import FamilyFormFactor
from app.schemas.order.shipping import (
    ShippingResponse,
    ShippingListResponse,
    UserMini,
)


router = APIRouter(prefix="/shippings", tags=["Shipping"])


def _fetch_recipients_lookup(
    db: Session,
    shippings: list[Shipping],
) -> dict[int, list[UserMini]]:
    """Return ``{shipping_id: [UserMini, ...]}`` of part recipients.

    A shipment's "Recipients" are the build-request requestors who are
    grouped under that shipment's package recipient (handler) inside a
    build plan whose ``config_number`` matches the shipment's. The
    grouping comes from ``build_plan_shippings``; restricting by
    BuildRequest ensures only users who actually ordered for this config
    appear.
    """
    if not shippings:
        return {}

    pairs = {
        (s.config_number_id, s.recipient_user_id)
        for s in shippings
        if s.config_number_id is not None and s.recipient_user_id is not None
    }
    if not pairs:
        return {}

    config_ids = sorted({c for c, _ in pairs})
    handler_ids = sorted({h for _, h in pairs})

    sql = text("""
        SELECT
            bp.config_number_id      AS config_number_id,
            bps.recipient_user_id    AS handler_id,
            requestor.id             AS requestor_id,
            requestor.full_name      AS requestor_full_name,
            requestor.email          AS requestor_email
        FROM build_plan_shippings bps
        JOIN build_plans bp           ON bp.id = bps.build_plan_id
        JOIN users requestor          ON requestor.id = bps.requestor_user_id
        WHERE bp.config_number_id IN :config_ids
          AND bps.recipient_user_id IN :handler_ids
        GROUP BY
            bp.config_number_id,
            bps.recipient_user_id,
            requestor.id,
            requestor.full_name,
            requestor.email
        ORDER BY requestor.full_name
    """).bindparams(
        bindparam("config_ids", expanding=True),
        bindparam("handler_ids", expanding=True),
    )

    rows = db.execute(
        sql,
        {"config_ids": config_ids, "handler_ids": handler_ids},
    ).mappings().all()

    by_pair: dict[tuple[int, int], list[UserMini]] = {}
    for r in rows:
        key = (r["config_number_id"], r["handler_id"])
        if key not in pairs:
            continue
        by_pair.setdefault(key, []).append(
            UserMini(
                id=r["requestor_id"],
                full_name=r["requestor_full_name"],
                email=r["requestor_email"],
            )
        )

    result: dict[int, list[UserMini]] = {}
    for s in shippings:
        if s.config_number_id is None or s.recipient_user_id is None:
            result[s.id] = []
            continue
        result[s.id] = by_pair.get((s.config_number_id, s.recipient_user_id), [])
    return result


def _serialize(s: Shipping, recipients: list[UserMini] | None = None) -> ShippingResponse:
    return ShippingResponse(
        id=s.id,
        config_number=s.config_number.value if s.config_number else None,
        tracking_number=s.tracking_number,
        forwarder=s.forwarder.name if s.forwarder else None,
        quantity=s.quantity,
        comments=s.comments,
        ship_date=s.ship_date,
        eta=s.eta,
        delivery_date=s.delivery_date,
        status=s.status.value if hasattr(s.status, "value") else str(s.status),
        recipient_user=UserMini(
            id=s.recipient_user.id, full_name=s.recipient_user.full_name, email=s.recipient_user.email
        ) if s.recipient_user else None,
        recipients=recipients or [],
    )


@router.get("", response_model=ShippingListResponse)
def list_shippings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    family: Optional[str] = None,
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query(None, pattern="^(asc|desc)$"),
    my_plans: bool = Query(
        False,
        description=(
            "Restrict to shipments whose config_number is on a build plan the "
            "current user owns or edits (via family/form-factor access or "
            "per-plan override)."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("shipping:read")),
):
    q = (
        db.query(Shipping)
        .options(
            joinedload(Shipping.config_number),
            joinedload(Shipping.recipient_user),
            joinedload(Shipping.forwarder),
        )
    )

    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if statuses:
            q = q.filter(Shipping.status.in_(statuses))

    if family:
        family_codes = [f.strip() for f in family.split(",") if f.strip()]
        if family_codes:
            family_cfg_subq = (
                db.query(BuildPlan.config_number_id)
                .join(
                    FamilyFormFactor,
                    FamilyFormFactor.id == BuildPlan.family_form_factor_id,
                )
                .join(Family, Family.id == FamilyFormFactor.family_id)
                .filter(
                    BuildPlan.config_number_id.isnot(None),
                    Family.code.in_(family_codes),
                )
                .subquery()
            )
            q = q.filter(Shipping.config_number_id.in_(family_cfg_subq))

    if my_plans:
        family_owned_subq = (
            db.query(BuildPlanAccess.family_form_factor_id)
            .filter(
                BuildPlanAccess.user_id == current_user.id,
                BuildPlanAccess.access_type.in_(
                    [AccessTypeEnum.owner, AccessTypeEnum.editor]
                ),
            )
            .subquery()
        )
        plan_owned_subq = (
            db.query(BuildPlanAccessOverride.build_plan_id)
            .filter(
                BuildPlanAccessOverride.user_id == current_user.id,
                BuildPlanAccessOverride.access_type.in_(
                    [AccessTypeEnum.owner, AccessTypeEnum.editor]
                ),
            )
            .subquery()
        )
        owned_cfg_subq = (
            db.query(BuildPlan.config_number_id)
            .filter(
                BuildPlan.config_number_id.isnot(None),
                or_(
                    BuildPlan.family_form_factor_id.in_(family_owned_subq),
                    BuildPlan.id.in_(plan_owned_subq),
                ),
            )
            .subquery()
        )
        q = q.filter(Shipping.config_number_id.in_(owned_cfg_subq))

    cfg_joined = False
    recipient_joined = False
    fwd_joined = False

    if search:
        like = f"%{search}%"
        q = q.outerjoin(ConfigNumber, Shipping.config_number_id == ConfigNumber.id)
        q = q.outerjoin(User, Shipping.recipient_user_id == User.id)
        q = q.outerjoin(Forwarder, Shipping.forwarder_id == Forwarder.id)
        cfg_joined = recipient_joined = fwd_joined = True
        q = q.filter(or_(
            ConfigNumber.value.ilike(like),
            Shipping.tracking_number.ilike(like),
            User.full_name.ilike(like),
            User.email.ilike(like),
            Forwarder.name.ilike(like),
        ))

    # Sorting
    sort_map = {
        "id": Shipping.id,
        "quantity": Shipping.quantity,
        "ship_date": Shipping.ship_date,
        "eta": Shipping.eta,
        "delivery_date": Shipping.delivery_date,
        "status": Shipping.status,
        "tracking_number": Shipping.tracking_number,
    }
    key = (sort_by or "id").lower()
    sort_col = sort_map.get(key, Shipping.id)
    extra_order: list = []
    if key == "config_number":
        if not cfg_joined:
            q = q.outerjoin(ConfigNumber, Shipping.config_number_id == ConfigNumber.id)
            cfg_joined = True
        sort_col = ConfigNumber.value
    elif key in ("handler", "recipient_user", "recipient"):
        # "Handler" and "Recipient" both refer to the single
        # ``recipient_user`` column under the merged schema.
        if not recipient_joined:
            q = q.outerjoin(User, Shipping.recipient_user_id == User.id)
            recipient_joined = True
        sort_col = User.full_name
    elif key == "forwarder":
        if not fwd_joined:
            q = q.outerjoin(Forwarder, Shipping.forwarder_id == Forwarder.id)
            fwd_joined = True
        sort_col = Forwarder.name
    elif key == "build_plan_recency":
        # Order by latest matching build plan's (year, work_week) — used
        # by the PM dashboard "Recent Shipments" tile. Match via shared
        # config_number_id.
        year_subq = (
            select(func.max(BuildPlan.year))
            .where(BuildPlan.config_number_id == Shipping.config_number_id)
            .correlate(Shipping)
            .scalar_subquery()
        )
        ww_subq = (
            select(func.max(BuildPlan.work_week))
            .where(
                BuildPlan.config_number_id == Shipping.config_number_id,
                BuildPlan.year == year_subq,
            )
            .correlate(Shipping)
            .scalar_subquery()
        )
        sort_col = year_subq
        extra_order.append(
            ww_subq.desc() if (sort_order or "desc").lower() != "asc" else ww_subq.asc()
        )

    desc = (sort_order or "desc").lower() != "asc"
    order_clause = sort_col.desc() if desc else sort_col.asc()

    total = q.count()
    rows = (
        q.order_by(order_clause, *extra_order, Shipping.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    recipients_by_id = _fetch_recipients_lookup(db, rows)

    return ShippingListResponse(
        data=[_serialize(r, recipients_by_id.get(r.id, [])) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{shipping_id}", response_model=ShippingResponse)
def get_shipping(
    shipping_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:read")),
):
    s = (
        db.query(Shipping)
        .options(
            joinedload(Shipping.config_number),
            joinedload(Shipping.recipient_user),
            joinedload(Shipping.forwarder),
        )
        .filter(Shipping.id == shipping_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Shipping not found")
    recipients_by_id = _fetch_recipients_lookup(db, [s])
    return _serialize(s, recipients_by_id.get(s.id, []))