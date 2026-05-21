"""Aggregation queries powering the Business Overview dashboard.

Definitions used throughout this module:

* **Builds** = ``COUNT(build_plans.id)``
* **Boards** = ``SUM(build_requests.quantity)`` taken only over build requests
  that are the **latest revision** in their revision chain (i.e. no other
  ``BuildRequest`` references them via ``previous_build_request_id``).
  Build requests in ``Draft``, ``Cancelled`` or ``Rejected`` status are
  excluded. If a latest-revision OR is linked to multiple build plans its
  full quantity is attributed to each build plan it is linked to.
* **Year filter** is applied against ``build_plans.ship_date``.
* **Milestone build** = build plan whose support activity is named
  ``"Milestone"`` (case-insensitive).

All functions accept the same ``DashboardFilters`` object so the caller can
implement cross-filtering by passing the same filter set to every endpoint.
"""

from __future__ import annotations

import threading
import time
from typing import List, Optional

from sqlalchemy import case, distinct, extract, func
from sqlalchemy.orm import Session

from app.models.build.build_plan import (
    BuildPlan,
    BuildPlanStatus,
    SupportActivity,
)
from app.models.build.build_plan_component import BuildPlanComponent
from app.models.build.build_plan_build_request import BuildPlanBuildRequest
from app.models.build.build_plan_revision import BuildPlanRevision
from app.models.build.warehouse import QuantityStoredInWarehouse
from app.models.build.component import Component, ComponentSlot
from app.models.build.component_attribute_value import ComponentAttributeValue
from app.models.build.attribute_definition import AttributeDefinition
from app.models.build.family import Family
from app.models.build.family_form_factor import FamilyFormFactor
from app.models.build.form_factor import FormFactor
from app.models.build.silicon_stepping import (
    SiliconStepping,
    BuildPlanSiliconStepping,
)
from app.models.build.supplier import Supplier
from app.models.order.build_request import BuildRequest, BuildRequestStatus
from app.schemas.build.dashboard import (
    CategoryCount,
    ComponentSlotOption,
    FamilyAttributeBreakdown,
    FamilyAttributeBreakdownResponse,
    FamilyBreakdown,
    FamilyBreakdownResponse,
    FamilyComparisonResponse,
    FamilyComparisonFormFactorRow,
    FilterLookupResponse,
    FormFactorValue,
    KpiResponse,
    MilestoneTimelinePoint,
    RequiredQtyRow,
    StackedBarResponse,
    StackedBarRow,
    SupplierComponentResponse,
    SupplierComponentRow,
    SupplierComponentDetailResponse,
    SupplierComponentDetailRow,
    PcbSupplierCountResponse,
    PcbSupplierCountRow,
)


_MILESTONE_NAME = "Milestone"
_EXCLUDED_OR_STATUSES = (
    BuildRequestStatus.draft,
    BuildRequestStatus.cancelled,
    BuildRequestStatus.rejected,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _apply_build_plan_filters(query, filters):
    """Attach the standard set of joins + WHERE clauses to a query whose
    primary table is ``BuildPlan``. Caller is responsible for SELECT/GROUP.

    Status filtering targets the *latest revision's* ``status_at_revision``
    (falling back to ``BuildPlan.status`` if a plan has no revision yet),
    so that the Overview reflects the same status the tracker shows.
    """
    query = (
        query.join(FamilyFormFactor, BuildPlan.family_form_factor_id == FamilyFormFactor.id)
        .join(Family, FamilyFormFactor.family_id == Family.id)
        .join(FormFactor, FamilyFormFactor.form_factor_id == FormFactor.id)
        .join(SupportActivity, BuildPlan.support_activity_id == SupportActivity.id)
        .outerjoin(
            BuildPlanRevision,
            BuildPlanRevision.id == BuildPlan.latest_revision_id,
        )
    )

    # Latest-revision status; fall back to BuildPlan.status for plans that
    # somehow have no revision row (e.g. mid-import).
    latest_status_col = func.coalesce(
        BuildPlanRevision.status_at_revision, BuildPlan.status
    )

    if filters.year is not None:
        query = query.filter(BuildPlan.year == filters.year)
    if filters.family_codes:
        query = query.filter(Family.code.in_(filters.family_codes))
    if filters.form_factors:
        # Frontend FormFactor filter is keyed by FormFactor.name (the user-facing label).
        query = query.filter(FormFactor.name.in_(filters.form_factors))
    if filters.support_activities:
        query = query.filter(SupportActivity.name.in_(filters.support_activities))
    if filters.statuses:
        query = query.filter(latest_status_col.in_(filters.statuses))
    else:
        # Cancelled build plans are excluded from every dashboard widget by
        # default. Callers that explicitly filter by status (incl. Cancelled)
        # override this behaviour.
        query = query.filter(latest_status_col != BuildPlanStatus.cancelled)

    if filters.silicon_steppings:
        # Subquery: build_plan ids that have at least one of the selected
        # steppings linked via the silicon_steppings m2m table.
        from sqlalchemy import exists

        stepping_exists = (
            exists()
            .where(BuildPlanSiliconStepping.build_plan_id == BuildPlan.id)
            .where(
                BuildPlanSiliconStepping.silicon_stepping_id == SiliconStepping.id
            )
            .where(SiliconStepping.name.in_(filters.silicon_steppings))
        )
        query = query.filter(stepping_exists)

    return query


def _boards_subquery(db: Session):
    """Subquery yielding ``(build_plan_id, boards)`` where boards is:

        SUM(latest-revision build_request.quantity)
      + SUM(quantity_stored_in_warehouse.quantity_stored)

    Latest revision = the OR at the tip of the ``previous_build_request_id``
    chain (no other OR points back to it). Draft / Cancelled / Rejected ORs
    are excluded. Warehouse quantities have no status filter.
    """
    from sqlalchemy import exists
    from sqlalchemy.orm import aliased

    OR2 = aliased(BuildRequest)
    is_latest_revision = ~(
        exists().where(OR2.previous_build_request_id == BuildRequest.id)
    )

    # Part A: latest-revision OR quantity per build plan.
    or_sq = (
        db.query(
            BuildPlanBuildRequest.build_plan_id.label("build_plan_id"),
            func.coalesce(func.sum(BuildRequest.quantity), 0).label("qty"),
        )
        .join(BuildRequest, BuildRequest.id == BuildPlanBuildRequest.build_request_id)
        .filter(~BuildRequest.status.in_(_EXCLUDED_OR_STATUSES))
        .filter(is_latest_revision)
        .group_by(BuildPlanBuildRequest.build_plan_id)
        .subquery()
    )

    # Part B: warehouse stored quantity per build plan.
    wh_sq = (
        db.query(
            QuantityStoredInWarehouse.buildplan_id.label("build_plan_id"),
            func.coalesce(
                func.sum(QuantityStoredInWarehouse.quantity_stored), 0
            ).label("qty"),
        )
        .group_by(QuantityStoredInWarehouse.buildplan_id)
        .subquery()
    )

    # Union both parts and sum per build plan.
    from sqlalchemy import union_all, literal_column, select

    combined = union_all(
        select(
            or_sq.c.build_plan_id.label("build_plan_id"),
            or_sq.c.qty.label("qty"),
        ),
        select(
            wh_sq.c.build_plan_id.label("build_plan_id"),
            wh_sq.c.qty.label("qty"),
        ),
    ).subquery()

    boards_sq = (
        db.query(
            combined.c.build_plan_id.label("build_plan_id"),
            func.sum(combined.c.qty).label("boards"),
        )
        .group_by(combined.c.build_plan_id)
        .subquery()
    )

    return boards_sq


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------


def get_kpis(db: Session, filters) -> KpiResponse:
    boards_sq = _boards_subquery(db)

    q = (
        db.query(
            func.count(distinct(BuildPlan.id)).label("builds"),
            func.coalesce(func.sum(boards_sq.c.boards), 0.0).label("boards"),
            func.sum(
                case(
                    (func.lower(SupportActivity.name) == _MILESTONE_NAME.lower(), 1),
                    else_=0,
                )
            ).label("milestones"),
        )
        .select_from(BuildPlan)
        .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
    )
    q = _apply_build_plan_filters(q, filters)
    row = q.one()

    # Families and Form Factors are catalog totals (count of rows in their
    # reference tables) — not derived from the filtered build-plan scope.
    total_families = db.query(func.count(Family.id)).scalar() or 0
    total_form_factors = db.query(func.count(FormFactor.id)).scalar() or 0

    return KpiResponse(
        total_builds=int(row.builds or 0),
        total_boards=float(row.boards or 0),
        total_families=int(total_families),
        total_form_factors=int(total_form_factors),
        milestone_builds=int(row.milestones or 0),
    )


# ---------------------------------------------------------------------------
# Family x FormFactor breakdowns (donut grid)
# ---------------------------------------------------------------------------


def get_family_breakdown(db: Session, filters, metric: str) -> FamilyBreakdownResponse:
    """metric ∈ {"boards", "builds"}.

    Executes the exact query defined in ``db/queries/family_form_factor_breakdown.sql``
    (with optional WHERE clauses appended for the dashboard filters) and
    maps the rows directly into the donut-grid response. This guarantees
    the donut numbers match the SQL output 1:1.
    """

    from sqlalchemy import text

    # Status filtering targets the latest revision's status_at_revision
    # (falling back to bp.status when no revision exists), matching the
    # behaviour of `_apply_build_plan_filters` used by the other widgets.
    # Cast to text so the value can be compared against the bound text[]
    # parameter (PostgreSQL has no implicit enum <-> text cast).
    latest_status_sql = (
        "COALESCE(bpr.status_at_revision, bp.status)::text"
    )

    def _to_db_status(value: str) -> str:
        """Map a frontend status string (e.g. ``"Done"``) to the PostgreSQL
        enum label (lowercase, matches ``BuildPlanStatus`` member names).
        Accepts either the enum value or the enum name; falls back to the
        original (lowercased) string for forward compatibility."""
        if not value:
            return value
        try:
            return BuildPlanStatus(value).name
        except ValueError:
            try:
                return BuildPlanStatus[value].name
            except KeyError:
                return value.lower()

    conds = [f"{latest_status_sql} <> 'cancelled'"] if not filters.statuses else []
    params: dict[str, object] = {}

    if filters.statuses:
        conds.append(f"{latest_status_sql} = ANY(:statuses)")
        params["statuses"] = [_to_db_status(s) for s in filters.statuses]
    if filters.year is not None:
        conds.append("bp.year = :year")
        params["year"] = int(filters.year)
    if filters.family_codes:
        conds.append("f.code = ANY(:family_codes)")
        params["family_codes"] = list(filters.family_codes)
    if filters.form_factors:
        # Frontend FormFactor filter is keyed by FormFactor.name (the user-facing label).
        conds.append("s.name = ANY(:form_factors)")
        params["form_factors"] = list(filters.form_factors)
    if filters.support_activities:
        conds.append(
            "EXISTS (SELECT 1 FROM support_activities sa "
            "WHERE sa.id = bp.support_activity_id "
            "AND sa.name = ANY(:support_activities))"
        )
        params["support_activities"] = list(filters.support_activities)
    if filters.silicon_steppings:
        conds.append(
            "EXISTS (SELECT 1 FROM build_plan_silicon_steppings bpss "
            "JOIN silicon_steppings ss ON ss.id = bpss.silicon_stepping_id "
            "WHERE bpss.build_plan_id = bp.id "
            "AND ss.name = ANY(:silicon_steppings))"
        )
        params["silicon_steppings"] = list(filters.silicon_steppings)

    where_clause = "\n      AND ".join(conds)
    where_sql = f"WHERE {where_clause}" if where_clause else ""

    sql = text(
        f"""
WITH latest_or AS (
    SELECT
        bpor.build_plan_id,
        COALESCE(SUM(o.quantity), 0) AS or_qty
    FROM build_plan_build_requests bpor
    JOIN build_requests o ON o.id = bpor.build_request_id
    WHERE o.status NOT IN ('draft', 'cancelled', 'rejected')
      AND NOT EXISTS (
          SELECT 1 FROM build_requests o2
          WHERE o2.previous_build_request_id = o.id
      )
    GROUP BY bpor.build_plan_id
),
wh AS (
    SELECT
        buildplan_id AS build_plan_id,
        COALESCE(SUM(quantity_stored), 0) AS wh_qty
    FROM quantity_stored_in_warehouse
    GROUP BY buildplan_id
),
bp_family_form_factor AS (
    SELECT
        bp.id                                             AS build_plan_id,
        f.code                                            AS family_code,
        f.name                                            AS family_name,
        s.name                                            AS form_factor,
        COALESCE(lor.or_qty, 0) + COALESCE(wh.wh_qty, 0)  AS boards
    FROM build_plans   bp
    JOIN family_form_factors   fs  ON fs.id = bp.family_form_factor_id
    JOIN families      f   ON f.id  = fs.family_id
    JOIN form_factors  s   ON s.id  = fs.form_factor_id
    LEFT JOIN build_plan_revisions bpr ON bpr.id = bp.latest_revision_id
    LEFT JOIN latest_or lor ON lor.build_plan_id = bp.id
    LEFT JOIN wh            ON wh.build_plan_id  = bp.id
    {where_sql}
)
SELECT
    family_code,
    family_name,
    form_factor,
    COUNT(*)                  AS builds,
    COALESCE(SUM(boards), 0)  AS boards
FROM bp_family_form_factor
GROUP BY family_code, family_name, form_factor
ORDER BY family_code, form_factor
"""
    )

    rows = db.execute(sql, params).mappings().all()

    families_map: dict[str, FamilyBreakdown] = {}
    for row in rows:
        fam = families_map.get(row["family_code"])
        if fam is None:
            fam = FamilyBreakdown(
                family_code=row["family_code"],
                family_name=row["family_name"],
                total=0.0,
                form_factors=[],
            )
            families_map[row["family_code"]] = fam
        v = float(row["boards"] if metric == "boards" else row["builds"]) or 0.0
        fam.form_factors.append(
            FormFactorValue(
                form_factor=row["form_factor"],
                value=v,
            )
        )
        fam.total += v

    return FamilyBreakdownResponse(
        metric=metric, families=list(families_map.values())
    )



# ---------------------------------------------------------------------------
# Family × Attribute pie grid (Si Stepping / PCB Revision / HW Revision)
# ---------------------------------------------------------------------------


def get_family_attribute_breakdown(
    db: Session, filters
) -> FamilyAttributeBreakdownResponse:
    """Per-family build-count breakdowns for Silicon Stepping, PCB Revision
    and HW Revision.

    Uses the same build-plan scope as the Family × FormFactor breakdown (cancelled
    build plans excluded by default; explicit status filter overrides) so
    the donut grid and these pies stay in lockstep.
    """

    # --- Silicon Stepping (m2m table, not a component attribute) -----------
    si_q = (
        db.query(
            Family.code.label("family_code"),
            Family.name.label("family_name"),
            SiliconStepping.name.label("label"),
            func.count(distinct(BuildPlan.id)).label("c"),
        )
        .select_from(BuildPlan)
        .join(
            BuildPlanSiliconStepping,
            BuildPlanSiliconStepping.build_plan_id == BuildPlan.id,
        )
        .join(
            SiliconStepping,
            SiliconStepping.id == BuildPlanSiliconStepping.silicon_stepping_id,
        )
    )
    si_q = _apply_build_plan_filters(si_q, filters)
    si_q = si_q.group_by(Family.code, Family.name, SiliconStepping.name)

    # --- Generic component-attribute breakdown per family ------------------
    def _family_attr_breakdown(component_name: str, attribute_name: str):
        q = (
            db.query(
                Family.code.label("family_code"),
                Family.name.label("family_name"),
                ComponentAttributeValue.value_text.label("label"),
                func.count(distinct(BuildPlan.id)).label("c"),
            )
            .select_from(BuildPlan)
            .join(
                BuildPlanComponent,
                BuildPlanComponent.build_plan_id == BuildPlan.id,
            )
            .join(Component, Component.id == BuildPlanComponent.component_id)
            .join(
                ComponentAttributeValue,
                ComponentAttributeValue.build_plan_component_id
                == BuildPlanComponent.id,
            )
            .join(
                AttributeDefinition,
                AttributeDefinition.id == ComponentAttributeValue.attribute_id,
            )
            .filter(Component.name == component_name)
            .filter(AttributeDefinition.name == attribute_name)
            .filter(ComponentAttributeValue.value_text.isnot(None))
        )
        q = _apply_build_plan_filters(q, filters)
        q = q.group_by(
            Family.code, Family.name, ComponentAttributeValue.value_text
        )
        return q.all()

    pcb_rows = _family_attr_breakdown("PCB", "Revision")
    hw_rows = _family_attr_breakdown("HW", "Revision")
    si_rows = si_q.all()

    families: dict[str, FamilyAttributeBreakdown] = {}

    def _ensure(code: str, name: str) -> FamilyAttributeBreakdown:
        fam = families.get(code)
        if fam is None:
            fam = FamilyAttributeBreakdown(
                family_code=code,
                family_name=name,
                silicon_steppings=[],
                pcb_revisions=[],
                hw_revisions=[],
            )
            families[code] = fam
        return fam

    for r in si_rows:
        fam = _ensure(r.family_code, r.family_name)
        fam.silicon_steppings.append(
            CategoryCount(label=r.label or "Unknown", value=float(r.c or 0))
        )
    for r in pcb_rows:
        fam = _ensure(r.family_code, r.family_name)
        fam.pcb_revisions.append(
            CategoryCount(label=r.label or "Unknown", value=float(r.c or 0))
        )
    for r in hw_rows:
        fam = _ensure(r.family_code, r.family_name)
        fam.hw_revisions.append(
            CategoryCount(label=r.label or "Unknown", value=float(r.c or 0))
        )

    # Sort slices within each family (largest first) and families by code.
    for fam in families.values():
        fam.silicon_steppings.sort(key=lambda c: c.value, reverse=True)
        fam.pcb_revisions.sort(key=lambda c: c.value, reverse=True)
        fam.hw_revisions.sort(key=lambda c: c.value, reverse=True)

    ordered = sorted(families.values(), key=lambda f: f.family_code)
    return FamilyAttributeBreakdownResponse(families=ordered)



# ---------------------------------------------------------------------------
# Support Activity x FormFactor stacked bar
# ---------------------------------------------------------------------------


def get_support_activity_breakdown(
    db: Session, filters, metric: str
) -> StackedBarResponse:
    if metric == "boards":
        boards_sq = _boards_subquery(db)
        value_expr = func.coalesce(func.sum(boards_sq.c.boards), 0.0)
        q = (
            db.query(
                SupportActivity.name.label("support_activity"),
                FormFactor.name.label("form_factor"),
                value_expr.label("value"),
            )
            .select_from(BuildPlan)
            .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
        )
    else:
        value_expr = func.count(distinct(BuildPlan.id))
        q = (
            db.query(
                SupportActivity.name.label("support_activity"),
                FormFactor.name.label("form_factor"),
                value_expr.label("value"),
            )
            .select_from(BuildPlan)
        )

    q = _apply_build_plan_filters(q, filters)
    q = q.group_by(SupportActivity.name, FormFactor.name).order_by(
        SupportActivity.name, FormFactor.name
    )

    rows = [
        StackedBarRow(
            support_activity=r.support_activity,
            form_factor=r.form_factor,
            value=float(r.value or 0),
        )
        for r in q.all()
    ]
    return StackedBarResponse(metric=metric, rows=rows)


# ---------------------------------------------------------------------------
# Silicon stepping pie (Builds by Silicon Stepping)
# ---------------------------------------------------------------------------


def get_silicon_stepping_breakdown(db: Session, filters):
    """Returns list of {label, value} where value = build count per stepping."""

    q = (
        db.query(
            SiliconStepping.name.label("stepping"),
            func.count(distinct(BuildPlan.id)).label("value"),
        )
        .select_from(BuildPlan)
        .join(
            BuildPlanSiliconStepping,
            BuildPlanSiliconStepping.build_plan_id == BuildPlan.id,
        )
        .join(
            SiliconStepping,
            SiliconStepping.id == BuildPlanSiliconStepping.silicon_stepping_id,
        )
    )
    q = _apply_build_plan_filters(q, filters)
    q = q.group_by(SiliconStepping.name).order_by(
        func.count(distinct(BuildPlan.id)).desc()
    )

    return [
        CategoryCount(label=r.stepping or "Unknown", value=float(r.value or 0))
        for r in q.all()
    ]


def _silicon_stepping_breakdown_by_form_factor(db: Session, filters):
    """Per-FormFactor breakdown of silicon-stepping build counts. Returns a dict
    ``{form_factor_name: [CategoryCount, ...]}`` for use by the family comparison
    panel.
    """
    q = (
        db.query(
            FormFactor.name.label("form_factor"),
            SiliconStepping.name.label("stepping"),
            func.count(distinct(BuildPlan.id)).label("c"),
        )
        .select_from(BuildPlan)
        .join(
            BuildPlanSiliconStepping,
            BuildPlanSiliconStepping.build_plan_id == BuildPlan.id,
        )
        .join(
            SiliconStepping,
            SiliconStepping.id == BuildPlanSiliconStepping.silicon_stepping_id,
        )
    )
    q = _apply_build_plan_filters(q, filters)
    q = q.group_by(FormFactor.name, SiliconStepping.name)

    grouped: dict[str, list[CategoryCount]] = {}
    for r in q.all():
        grouped.setdefault(r.form_factor, []).append(
            CategoryCount(label=r.stepping or "Unknown", value=float(r.c or 0))
        )
    return grouped


# ---------------------------------------------------------------------------
# Filter lookups (for dropdowns)
# ---------------------------------------------------------------------------


# Module-level TTL cache for filter dropdowns. These values change slowly
# (new family/FormFactor/support-activity rows are rare) and are fetched on every
# dashboard load, so caching for a few minutes gives a large speed-up at the
# cost of brief staleness. Call ``invalidate_filter_lookups_cache()`` after
# bulk imports that may have introduced new lookup rows.
_LOOKUP_CACHE_TTL_SECONDS = 300
_lookup_cache_lock = threading.Lock()
_lookup_cache: dict[str, object] = {"value": None, "expires_at": 0.0}


def invalidate_filter_lookups_cache() -> None:
    """Drop the cached dashboard lookups so the next request re-queries."""
    with _lookup_cache_lock:
        _lookup_cache["value"] = None
        _lookup_cache["expires_at"] = 0.0


def get_filter_lookups(db: Session) -> FilterLookupResponse:
    now = time.monotonic()
    cached = _lookup_cache.get("value")
    if cached is not None and float(_lookup_cache.get("expires_at", 0.0)) > now:
        return cached  # type: ignore[return-value]

    families = [
        CategoryCount(label=f"{c} - {n}", value=0)
        for (c, n) in db.query(Family.code, Family.name).order_by(Family.code).all()
    ]
    form_factors = [
        CategoryCount(label=n, value=0)
        for (n,) in db.query(FormFactor.name).order_by(FormFactor.name).all()
    ]
    support_activities = [
        n for (n,) in db.query(SupportActivity.name).order_by(SupportActivity.name).all()
    ]
    statuses = [s.value for s in BuildPlanStatus]

    si_steppings = [
        v
        for (v,) in db.query(SiliconStepping.name)
        .filter(SiliconStepping.name.isnot(None))
        .order_by(SiliconStepping.name)
        .all()
    ]

    years_raw = (
        db.query(distinct(BuildPlan.year))
        .filter(BuildPlan.year.isnot(None))
        .order_by(BuildPlan.year.desc())
        .all()
    )
    years = [int(y[0]) for y in years_raw if y[0] is not None]

    components = [
        n
        for (n,) in db.query(Component.name)
        .join(BuildPlanComponent, BuildPlanComponent.component_id == Component.id)
        .filter(Component.name.isnot(None))
        .distinct()
        .order_by(Component.name)
        .all()
    ]

    component_slot_rows = (
        db.query(Component.name, ComponentSlot.slot_code)
        .join(BuildPlanComponent, BuildPlanComponent.component_id == Component.id)
        .outerjoin(ComponentSlot, ComponentSlot.id == BuildPlanComponent.slot_id)
        .filter(Component.name.isnot(None))
        .distinct()
        .order_by(Component.name, ComponentSlot.slot_code)
        .all()
    )
    component_slots = [
        ComponentSlotOption(component_name=name, slot_code=slot_code)
        for (name, slot_code) in component_slot_rows
    ]

    response = FilterLookupResponse(
        families=families,
        form_factors=form_factors,
        support_activities=support_activities,
        statuses=statuses,
        silicon_steppings=si_steppings,
        years=years,
        components=components,
        component_slots=component_slots,
    )

    with _lookup_cache_lock:
        _lookup_cache["value"] = response
        _lookup_cache["expires_at"] = time.monotonic() + _LOOKUP_CACHE_TTL_SECONDS

    return response


# ---------------------------------------------------------------------------
# Phase 2 â€” Required-Qty top contributors
# ---------------------------------------------------------------------------


def get_required_quantity_top(db: Session, filters, limit: int = 15):
    value_expr = func.coalesce(func.sum(BuildPlan.required_quantity), 0)
    q = (
        db.query(
            Family.code.label("family_code"),
            FormFactor.name.label("form_factor"),
            value_expr.label("value"),
        )
        .select_from(BuildPlan)
    )
    q = _apply_build_plan_filters(q, filters)
    q = (
        q.group_by(Family.code, FormFactor.name)
        .order_by(value_expr.desc())
        .limit(limit)
    )
    return [
        RequiredQtyRow(
            family_code=r.family_code,
            form_factor=r.form_factor,
            required_quantity=int(r.value or 0),
        )
        for r in q.all()
    ]


# ---------------------------------------------------------------------------
# Phase 2 â€” Milestone timeline (monthly)
# ---------------------------------------------------------------------------


def get_milestone_timeline(db: Session, filters, metric: str = "builds"):
    """Monthly Milestone series bucketed by (year, work_week) derived from
    the config number.

    The config number embeds the ISO year+work-week (``<Family><YY><WW>``),
    so we group by those denormalised columns instead of ``build_start_date``
    (which is frequently missing on early-stage plans). Each (year, ww) bucket
    is mapped to the calendar month containing the Monday of that ISO week so
    the result is still a "YYYY-MM" series that the existing column chart can
    render unchanged.

    ``metric`` controls the Y value:
    * ``"builds"`` (default) — distinct count of Milestone build plans
    * ``"boards"`` — sum of board quantities (latest-revision build requests
      + warehouse-stored quantities) across those plans
    """

    from datetime import date

    if metric == "boards":
        boards_sq = _boards_subquery(db)
        value_expr = func.coalesce(func.sum(boards_sq.c.boards), 0.0)
        q = (
            db.query(
                BuildPlan.year.label("y"),
                BuildPlan.work_week.label("w"),
                value_expr.label("value"),
            )
            .select_from(BuildPlan)
            .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
        )
    else:
        q = (
            db.query(
                BuildPlan.year.label("y"),
                BuildPlan.work_week.label("w"),
                func.count(distinct(BuildPlan.id)).label("value"),
            )
            .select_from(BuildPlan)
        )

    q = _apply_build_plan_filters(q, filters)
    q = (
        q.filter(BuildPlan.year.isnot(None))
        .filter(BuildPlan.work_week.isnot(None))
        .filter(func.lower(SupportActivity.name) == _MILESTONE_NAME.lower())
        .group_by(BuildPlan.year, BuildPlan.work_week)
        .order_by(BuildPlan.year, BuildPlan.work_week)
    )

    # Roll up (year, work_week) -> "YYYY-MM" in Python: multiple ISO weeks
    # can map to the same calendar month, so we sum into a dict and emit
    # the ordered series at the end.
    monthly: dict[str, float] = {}
    for r in q.all():
        try:
            iso_year = int(r.y)
            iso_week = int(r.w)
            # Monday of the ISO week.
            monday = date.fromisocalendar(iso_year, iso_week, 1)
        except (TypeError, ValueError):
            continue
        period = f"{monday.year:04d}-{monday.month:02d}"
        monthly[period] = monthly.get(period, 0.0) + float(r.value or 0)

    return [
        MilestoneTimelinePoint(period=p, count=int(round(c)))
        for p, c in sorted(monthly.items())
    ]


# ---------------------------------------------------------------------------
# Phase 2 â€” Per-Family comparison
# ---------------------------------------------------------------------------


def get_family_comparison(db: Session, filters, family_code: str) -> FamilyComparisonResponse:
    """For one family: per-FormFactor breakdown of Si Stepping, PCB Revision, totals."""

    fam_row = db.query(Family).filter(Family.code == family_code).one_or_none()
    if fam_row is None:
        return FamilyComparisonResponse(
            family_code=family_code, family_name=family_code, form_factors=[]
        )

    # Pin the family scope on a per-call basis (does not mutate caller).
    scoped = filters.model_copy(update={"family_codes": [family_code]})

    # Totals per FormFactor.
    boards_sq = _boards_subquery(db)
    totals_q = (
        db.query(
            FormFactor.name.label("form_factor"),
            func.count(distinct(BuildPlan.id)).label("builds"),
            func.coalesce(func.sum(boards_sq.c.boards), 0.0).label("boards"),
        )
        .select_from(BuildPlan)
        .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
    )
    totals_q = _apply_build_plan_filters(totals_q, scoped)
    totals_q = totals_q.group_by(FormFactor.name).order_by(FormFactor.name)

    form_factor_totals = {
        r.form_factor: {
            "builds": int(r.builds or 0),
            "boards": float(r.boards or 0),
        }
        for r in totals_q.all()
    }

    # Generic helper: count distinct build plans per (form_factor, attribute value)
    def _attr_breakdown(component_name: str, attribute_name: str):
        q = (
            db.query(
                FormFactor.name.label("form_factor"),
                ComponentAttributeValue.value_text.label("v"),
                func.count(distinct(BuildPlan.id)).label("c"),
            )
            .select_from(BuildPlan)
            .join(BuildPlanComponent, BuildPlanComponent.build_plan_id == BuildPlan.id)
            .join(Component, Component.id == BuildPlanComponent.component_id)
            .join(
                ComponentAttributeValue,
                ComponentAttributeValue.build_plan_component_id == BuildPlanComponent.id,
            )
            .join(
                AttributeDefinition,
                AttributeDefinition.id == ComponentAttributeValue.attribute_id,
            )
            .filter(Component.name == component_name)
            .filter(AttributeDefinition.name == attribute_name)
            .filter(ComponentAttributeValue.value_text.isnot(None))
        )
        q = _apply_build_plan_filters(q, scoped)
        q = q.group_by(FormFactor.name, ComponentAttributeValue.value_text)

        grouped: dict[str, list[CategoryCount]] = {}
        for r in q.all():
            grouped.setdefault(r.form_factor, []).append(
                CategoryCount(label=r.v or "Unknown", value=float(r.c or 0))
            )
        return grouped

    si_map = _silicon_stepping_breakdown_by_form_factor(db, scoped)
    pcb_map = _attr_breakdown("PCB", "Revision")

    form_factors = []
    for form_factor_name, agg in form_factor_totals.items():
        form_factors.append(
            FamilyComparisonFormFactorRow(
                form_factor=form_factor_name,
                silicon_steppings=si_map.get(form_factor_name, []),
                pcb_revisions=pcb_map.get(form_factor_name, []),
                total_builds=agg["builds"],
                total_boards=agg["boards"],
            )
        )

    return FamilyComparisonResponse(
        family_code=fam_row.code,
        family_name=fam_row.name,
        form_factors=form_factors,
    )


# ---------------------------------------------------------------------------
# Supplier × Component breakdown (pie chart)
# ---------------------------------------------------------------------------


def get_supplier_component_breakdown(
    db: Session,
    filters,
    component_name: str,
    metric: str = "builds",
    slot_code: Optional[str] = None,
) -> SupplierComponentResponse:
    """Return per-supplier aggregates for a specific component (and optional
    slot).  Each row represents one (component_slot, supplier) combination.

    * metric="builds"  → COUNT(DISTINCT build_plan_id) drives the pie
    * metric="boards"  → SUM(latest-revision OR qty + warehouse qty) drives the pie

    Both counts are always returned in the response.
    """
    boards_sq = _boards_subquery(db)

    # Build the component_slot label expression: "component / slot" or just
    # "component" when there is no slot.
    slot_label = func.coalesce(
        func.nullif(
            Component.name + " / " + ComponentSlot.slot_code,
            Component.name + " / ",
        ),
        Component.name,
    )

    q = (
        db.query(
            slot_label.label("component_slot"),
            func.coalesce(Supplier.name, "Unknown").label("supplier"),
            func.count(func.distinct(BuildPlan.id)).label("builds"),
            func.coalesce(func.sum(boards_sq.c.boards), 0.0).label("boards"),
        )
        .select_from(BuildPlan)
        .join(BuildPlanComponent, BuildPlanComponent.build_plan_id == BuildPlan.id)
        .join(Component, Component.id == BuildPlanComponent.component_id)
        .outerjoin(ComponentSlot, ComponentSlot.id == BuildPlanComponent.slot_id)
        .outerjoin(Supplier, Supplier.id == BuildPlanComponent.supplier_id)
        .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
    )

    q = _apply_build_plan_filters(q, filters)
    q = q.filter(Component.name == component_name)

    if slot_code is not None:
        q = q.filter(ComponentSlot.slot_code == slot_code)

    q = q.group_by(slot_label, func.coalesce(Supplier.name, "Unknown"))

    sort_expr = (
        func.coalesce(func.sum(boards_sq.c.boards), 0.0)
        if metric == "boards"
        else func.count(func.distinct(BuildPlan.id))
    )
    q = q.order_by(sort_expr.desc())

    rows = [
        SupplierComponentRow(
            component_slot=r.component_slot or component_name,
            supplier=r.supplier,
            builds=int(r.builds or 0),
            boards=float(r.boards or 0),
        )
        for r in q.all()
    ]

    return SupplierComponentResponse(
        metric=metric,
        component_name=component_name,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Supplier × Component DETAIL breakdown (table)
# ---------------------------------------------------------------------------


def get_supplier_component_detail(
    db: Session,
    filters,
    component_name: str,
    slot_code: Optional[str] = None,
) -> SupplierComponentDetailResponse:
    """Detailed table for the Component section.

    Each row is one unique combination of
    ``(component_slot, supplier, attribute-values)`` observed across the
    filtered build plans. For each row we return:

    * ``builds``            – number of distinct build plans matching the row
    * ``boards``            – SUM of latest-revision OR qty + warehouse qty
                              across those build plans
    * ``required_quantity`` – SUM of ``build_plans.required_quantity``
                              across those build plans
    * ``attributes``        – ``{attribute_name: value}`` for that BPC
    """
    boards_sq = _boards_subquery(db)

    slot_label_expr = func.coalesce(
        func.nullif(
            Component.name + " / " + ComponentSlot.slot_code,
            Component.name + " / ",
        ),
        Component.name,
    )

    # Fetch one row per BuildPlanComponent with its parent build plan info.
    base_q = (
        db.query(
            BuildPlanComponent.id.label("bpc_id"),
            BuildPlan.id.label("bp_id"),
            func.coalesce(BuildPlan.required_quantity, 0).label("req_qty"),
            func.coalesce(boards_sq.c.boards, 0.0).label("boards"),
            slot_label_expr.label("component_slot"),
            func.coalesce(Supplier.name, "Unknown").label("supplier"),
        )
        .select_from(BuildPlan)
        .join(BuildPlanComponent, BuildPlanComponent.build_plan_id == BuildPlan.id)
        .join(Component, Component.id == BuildPlanComponent.component_id)
        .outerjoin(ComponentSlot, ComponentSlot.id == BuildPlanComponent.slot_id)
        .outerjoin(Supplier, Supplier.id == BuildPlanComponent.supplier_id)
        .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
    )

    base_q = _apply_build_plan_filters(base_q, filters)
    base_q = base_q.filter(Component.name == component_name)
    if slot_code is not None:
        base_q = base_q.filter(ComponentSlot.slot_code == slot_code)

    bpc_rows = base_q.all()
    if not bpc_rows:
        return SupplierComponentDetailResponse(
            component_name=component_name,
            columns=[],
            rows=[],
        )

    bpc_ids = [r.bpc_id for r in bpc_rows]

    # Fetch all attribute values for those BPCs.
    attr_rows = (
        db.query(
            ComponentAttributeValue.build_plan_component_id.label("bpc_id"),
            AttributeDefinition.name.label("attr_name"),
            ComponentAttributeValue.value_text.label("value_text"),
            ComponentAttributeValue.value_number.label("value_number"),
        )
        .join(
            AttributeDefinition,
            AttributeDefinition.id == ComponentAttributeValue.attribute_id,
        )
        .filter(ComponentAttributeValue.build_plan_component_id.in_(bpc_ids))
        .all()
    )

    attrs_by_bpc: dict[int, dict[str, Optional[str]]] = {}
    column_order: list[str] = []
    seen_columns: set[str] = set()
    for a in attr_rows:
        bucket = attrs_by_bpc.setdefault(a.bpc_id, {})
        if a.value_text is not None:
            val: Optional[str] = a.value_text
        elif a.value_number is not None:
            val = str(a.value_number)
        else:
            val = None
        bucket[a.attr_name] = val
        if a.attr_name not in seen_columns:
            seen_columns.add(a.attr_name)
            column_order.append(a.attr_name)

    column_order.sort()

    # Aggregate by (slot, supplier, attribute-tuple).
    grouped: dict[tuple, dict] = {}
    for r in bpc_rows:
        attrs = attrs_by_bpc.get(r.bpc_id, {})
        attr_key = tuple((c, attrs.get(c)) for c in column_order)
        key = (r.component_slot or component_name, r.supplier, attr_key)

        cell = grouped.get(key)
        if cell is None:
            cell = {
                "component_slot": r.component_slot or component_name,
                "supplier": r.supplier,
                "attributes": dict(attr_key),
                "bp_ids": set(),
                "boards": 0.0,
                "required_quantity": 0,
            }
            grouped[key] = cell

        if r.bp_id not in cell["bp_ids"]:
            cell["bp_ids"].add(r.bp_id)
            cell["boards"] += float(r.boards or 0)
            cell["required_quantity"] += int(r.req_qty or 0)

    rows = [
        SupplierComponentDetailRow(
            component_slot=g["component_slot"],
            supplier=g["supplier"],
            attributes=g["attributes"],
            builds=len(g["bp_ids"]),
            boards=g["boards"],
            required_quantity=g["required_quantity"],
        )
        for g in grouped.values()
    ]

    rows.sort(
        key=lambda r: (r.component_slot, r.supplier, -r.boards, -r.builds)
    )

    return SupplierComponentDetailResponse(
        component_name=component_name,
        columns=column_order,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Count of <component_slot> (builds / boards) by PCB Supplier
# ---------------------------------------------------------------------------


def get_supplier_component_by_pcb_supplier(
    db: Session,
    filters,
    component_name: str,
    slot_code: Optional[str] = None,
) -> PcbSupplierCountResponse:
    """For build plans that contain the selected ``<component, slot>``,
    aggregate builds and boards grouped by the supplier of the build plan's
    ``PCB`` component.

    * ``builds`` = COUNT(DISTINCT build_plan_id)
    * ``boards`` = SUM(latest-revision OR qty + warehouse qty) per build plan,
                   attributed once per (build plan, pcb_supplier).
    """
    from sqlalchemy.orm import aliased

    boards_sq = _boards_subquery(db)

    # Resolve the PCB supplier for each build plan via a dedicated subquery
    # so that joining never duplicates rows when a build plan has multiple
    # PCB BuildPlanComponents with the same supplier.
    pcb_sq = (
        db.query(
            BuildPlanComponent.build_plan_id.label("build_plan_id"),
            func.coalesce(Supplier.name, "Unknown").label("pcb_supplier"),
        )
        .join(Component, Component.id == BuildPlanComponent.component_id)
        .outerjoin(Supplier, Supplier.id == BuildPlanComponent.supplier_id)
        .filter(Component.name == "PCB")
        .distinct()
        .subquery()
    )

    # Restrict to build plans that contain the selected (component, slot).
    target_bpc = aliased(BuildPlanComponent)
    target_component = aliased(Component)
    target_slot = aliased(ComponentSlot)

    q = (
        db.query(
            func.coalesce(pcb_sq.c.pcb_supplier, "Unknown").label("pcb_supplier"),
            func.count(distinct(BuildPlan.id)).label("builds"),
            func.coalesce(func.sum(boards_sq.c.boards), 0.0).label("boards"),
        )
        .select_from(BuildPlan)
        .join(target_bpc, target_bpc.build_plan_id == BuildPlan.id)
        .join(target_component, target_component.id == target_bpc.component_id)
        .outerjoin(target_slot, target_slot.id == target_bpc.slot_id)
        .outerjoin(pcb_sq, pcb_sq.c.build_plan_id == BuildPlan.id)
        .outerjoin(boards_sq, boards_sq.c.build_plan_id == BuildPlan.id)
    )

    q = _apply_build_plan_filters(q, filters)
    q = q.filter(target_component.name == component_name)
    if slot_code is not None:
        q = q.filter(target_slot.slot_code == slot_code)

    q = q.group_by(func.coalesce(pcb_sq.c.pcb_supplier, "Unknown"))
    q = q.order_by(func.count(distinct(BuildPlan.id)).desc())

    rows = [
        PcbSupplierCountRow(
            pcb_supplier=r.pcb_supplier,
            builds=int(r.builds or 0),
            boards=float(r.boards or 0),
        )
        for r in q.all()
    ]

    return PcbSupplierCountResponse(
        component_name=component_name,
        rows=rows,
    )
