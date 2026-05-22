"""Build Plan service — query/aggregation logic for build_plans endpoints.

Extracted from `app/api/v1/endpoints/build_plans.py` to keep route handlers
thin. Behavior is intentionally unchanged: response shapes and SQL match
the original endpoint exactly.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.schemas.build.build_plan import BuildPlanListQuery, BuildPlanSortBy, SortOrder


SORT_COLUMNS: dict[BuildPlanSortBy, str] = {
    BuildPlanSortBy.id: "bp.id",
    BuildPlanSortBy.build_plan_id: "bp.id",
    BuildPlanSortBy.config_number: "cn.value",
    BuildPlanSortBy.support_activity: "sa.name",
    BuildPlanSortBy.build_description: "bpd.description",
    BuildPlanSortBy.build_notes: "build_notes",
    BuildPlanSortBy.status: "bp.status",
    BuildPlanSortBy.product_code: "bp.product_code",
    BuildPlanSortBy.mm_number: "bp.mm_number",
    BuildPlanSortBy.ta_number: "bp.ta_number",
    BuildPlanSortBy.pba_number: "bp.pba_number",
    BuildPlanSortBy.as_number: "bp.as_number",
    BuildPlanSortBy.revision: "latest_rev.revision_number",
    BuildPlanSortBy.build_start_date: "bp.build_start_date",
    BuildPlanSortBy.ship_date: "bp.ship_date",
    BuildPlanSortBy.required_quantity: "bp.required_quantity",
    BuildPlanSortBy.estimated_yield: "bp.estimated_yield",
    BuildPlanSortBy.family_code: "f.code",
    BuildPlanSortBy.form_factor: "s.name",
    BuildPlanSortBy.year: "bp.year",
    BuildPlanSortBy.work_week: "bp.work_week",
}


# ---------------------------------------------------------------------------
# Query-string helpers
# ---------------------------------------------------------------------------

def split_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_sort_pairs(
    sort_by_value: str | None,
    sort_order_value: str | None,
) -> list[tuple[BuildPlanSortBy, SortOrder]]:
    """Parse comma-separated sort_by / sort_order into ordered pairs.

    The first pair is the primary key; subsequent pairs are tie-breakers.
    """
    fields = split_values(sort_by_value)
    orders = split_values(sort_order_value)

    if not fields:
        return [(BuildPlanSortBy.id, SortOrder.desc)]

    pairs: list[tuple[BuildPlanSortBy, SortOrder]] = []
    seen_fields: set[BuildPlanSortBy] = set()

    for index, raw_field in enumerate(fields):
        try:
            sort_field = BuildPlanSortBy(raw_field)
        except ValueError as exc:
            expected_values = ", ".join(s.value for s in BuildPlanSortBy)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sort_by '{raw_field}'. Expected one of: {expected_values}",
            ) from exc

        if index < len(orders):
            raw_order = orders[index]
        elif orders:
            raw_order = orders[-1]
        else:
            raw_order = SortOrder.asc.value

        try:
            sort_dir = SortOrder(raw_order)
        except ValueError as exc:
            expected_values = ", ".join(o.value for o in SortOrder)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sort_order '{raw_order}'. Expected one of: {expected_values}",
            ) from exc

        if sort_field in seen_fields:
            continue
        seen_fields.add(sort_field)
        pairs.append((sort_field, sort_dir))

    return pairs or [(BuildPlanSortBy.id, SortOrder.desc)]


# ---------------------------------------------------------------------------
# Internal helpers for nested aggregations (used by both list & detail)
# ---------------------------------------------------------------------------

def _fetch_components(db: Session, build_plan_ids: list[int]) -> list[dict]:
    nested = {"build_plan_ids": build_plan_ids}

    component_sql = text("""
        SELECT
            bpc.id AS build_plan_component_id,
            bpc.build_plan_id,
            c.name AS component_name,
            cs.slot_code AS component_slot,
            sup.name AS supplier_name
        FROM build_plan_components bpc
        JOIN components c ON c.id = bpc.component_id
        LEFT JOIN component_slots cs ON cs.id = bpc.slot_id
        LEFT JOIN suppliers sup ON sup.id = bpc.supplier_id
        WHERE bpc.build_plan_id IN :build_plan_ids
        ORDER BY bpc.build_plan_id, c.name, cs.slot_code
    """).bindparams(bindparam("build_plan_ids", expanding=True))

    attribute_sql = text("""
        SELECT
            bpc.build_plan_id,
            bpc.id AS build_plan_component_id,
            ad.name AS attribute_name,
            COALESCE(cav.value_text, cav.value_number::text) AS attribute_value
        FROM component_attribute_values cav
        JOIN build_plan_components bpc
            ON bpc.id = cav.build_plan_component_id
        JOIN attribute_definitions ad
            ON ad.id = cav.attribute_id
        WHERE bpc.build_plan_id IN :build_plan_ids
        ORDER BY bpc.build_plan_id, bpc.id, ad.name
    """).bindparams(bindparam("build_plan_ids", expanding=True))

    component_rows = db.execute(component_sql, nested).mappings().all()
    attribute_rows = db.execute(attribute_sql, nested).mappings().all()

    attributes_by_component: dict[int, list[dict]] = defaultdict(list)
    for row in attribute_rows:
        attributes_by_component[row["build_plan_component_id"]].append({
            "name": row["attribute_name"],
            "value": row["attribute_value"],
        })

    return [
        {
            "build_plan_id": row["build_plan_id"],
            "build_plan_component_id": row["build_plan_component_id"],
            "component_name": row["component_name"],
            "component_slot": row["component_slot"],
            "supplier": row["supplier_name"],
            "attributes": attributes_by_component[row["build_plan_component_id"]],
        }
        for row in component_rows
    ]


def _fetch_tests(db: Session, build_plan_ids: list[int]) -> list[dict]:
    nested = {"build_plan_ids": build_plan_ids}
    test_sql = text("""
        SELECT
            bpt.build_plan_id,
            t.name AS test_name,
            td.detail AS test_detail
        FROM build_plan_tests bpt
        JOIN tests t ON t.id = bpt.test_id
        LEFT JOIN test_details td ON td.id = bpt.test_detail_id
        WHERE bpt.build_plan_id IN :build_plan_ids
        ORDER BY bpt.build_plan_id, t.name, td.detail
    """).bindparams(bindparam("build_plan_ids", expanding=True))

    return [dict(r) for r in db.execute(test_sql, nested).mappings().all()]


def _fetch_orders(db: Session, build_plan_ids: list[int]) -> list[dict]:
    nested = {"build_plan_ids": build_plan_ids}
    order_sql = text("""
        SELECT
            bpor.build_plan_id,
            orq.id AS build_request_id,
            orq.requestor_id AS requestor_user_id,
            u.full_name AS requestor_name,
            orq.quantity
        FROM build_plan_build_requests bpor
        JOIN build_requests orq
            ON orq.id = bpor.build_request_id
        LEFT JOIN users u
            ON u.id = orq.requestor_id
        WHERE bpor.build_plan_id IN :build_plan_ids
        ORDER BY bpor.build_plan_id, u.full_name
    """).bindparams(bindparam("build_plan_ids", expanding=True))
    return [dict(r) for r in db.execute(order_sql, nested).mappings().all()]


def _fetch_recipients(db: Session, build_plan_ids: list[int]) -> list[dict]:
    """Fetch recipient<->requestor mapping from build_plan_shippings."""
    nested = {"build_plan_ids": build_plan_ids}
    sql = text("""
        SELECT
            bps.build_plan_id,
            recipient.id AS recipient_user_id,
            recipient.full_name AS recipient_full_name,
            recipient.email AS recipient_email,
            requestor.id AS requestor_user_id,
            requestor.full_name AS requestor_full_name,
            bps.quantity
        FROM build_plan_shippings bps
        LEFT JOIN users recipient ON recipient.id = bps.recipient_user_id
        LEFT JOIN users requestor ON requestor.id = bps.requestor_user_id
        WHERE bps.build_plan_id IN :build_plan_ids
        ORDER BY bps.build_plan_id, recipient.full_name, requestor.full_name
    """).bindparams(bindparam("build_plan_ids", expanding=True))
    return [dict(r) for r in db.execute(sql, nested).mappings().all()]


def _fetch_warehouses_multi(db: Session, build_plan_ids: list[int]) -> list[dict]:
    nested = {"build_plan_ids": build_plan_ids}
    sql = text("""
        SELECT
            bp.id AS build_plan_id,
            w.id AS warehouse_id,
            w.name AS warehouse_name,
            COALESCE(q.quantity_stored, 0) AS quantity_stored
        FROM build_plans bp
        CROSS JOIN warehouses w
        LEFT JOIN quantity_stored_in_warehouse q
            ON q.buildplan_id = bp.id
           AND q.warehouse_id = w.id
        WHERE bp.id IN :build_plan_ids
        ORDER BY bp.id, w.id
    """).bindparams(bindparam("build_plan_ids", expanding=True))
    return [dict(r) for r in db.execute(sql, nested).mappings().all()]


def _fetch_shipments_multi(db: Session, build_plan_ids: list[int]) -> list[dict]:
    nested = {"build_plan_ids": build_plan_ids}
    sql = text("""
        SELECT
            sh.id AS shipment_id,
            bp.id AS build_plan_id,
            cn.value AS config_number,
            sh.tracking_number,
            f.name AS forwarder,
            sh.quantity,
            sh.comments,
            sh.ship_date,
            sh.eta,
            sh.delivery_date,
            sh.status,
            recipient.id AS recipient_user_id,
            recipient.full_name AS recipient_full_name,
            recipient.email AS recipient_email,
            recipient.full_name AS handler_name
        FROM shippings sh
        JOIN config_numbers cn ON cn.id = sh.config_number_id
        JOIN build_plans bp ON bp.config_number_id = cn.id
        LEFT JOIN users recipient ON recipient.id = sh.recipient_user_id
        LEFT JOIN forwarders f ON f.id = sh.forwarder_id
        WHERE bp.id IN :build_plan_ids
        ORDER BY bp.id, sh.ship_date DESC, sh.id DESC
    """).bindparams(bindparam("build_plan_ids", expanding=True))
    return [dict(r) for r in db.execute(sql, nested).mappings().all()]


def _group_recipients(rows) -> list[dict]:
    """Collapse flat ``_fetch_recipients`` rows into per-recipient blocks.

    Output shape: ``[{recipient: UserMini|None, requestors: [...]}, ...]``.
    """
    blocks: dict[int, dict] = {}
    for r in rows:
        recipient_id = r.get("recipient_user_id")
        key = recipient_id if recipient_id is not None else 0
        block = blocks.get(key)
        if block is None:
            block = {
                "recipient": {
                    "id": recipient_id,
                    "full_name": r.get("recipient_full_name"),
                    "email": r.get("recipient_email"),
                } if recipient_id is not None else None,
                "requestors": [],
            }
            blocks[key] = block
        block["requestors"].append({
            "name": r.get("requestor_full_name"),
            "user_id": r.get("requestor_user_id"),
            "quantity": r.get("quantity"),
        })
    return list(blocks.values())


def _shipment_dict(row: dict) -> dict:
    status_value = row["status"]
    return {
        "shipment_id": row["shipment_id"],
        "config_number": row["config_number"],
        "tracking_number": row["tracking_number"],
        "forwarder": row["forwarder"],
        "quantity": row["quantity"],
        "comments": row["comments"],
        "ship_date": row["ship_date"],
        "eta": row["eta"],
        "delivery_date": row["delivery_date"],
        "status": status_value.value if hasattr(status_value, "value") else status_value,
        "recipient_user": {
            "id": row["recipient_user_id"],
            "full_name": row["recipient_full_name"],
            "email": row["recipient_email"],
        } if row["recipient_user_id"] else None,
        "handler_name": row["handler_name"],
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def list_build_plans(
    db: Session,
    query: BuildPlanListQuery,
    *,
    current_user_id: int,
) -> dict[str, Any]:
    offset = (query.page - 1) * query.page_size

    where_clauses: list[str] = []
    params: dict[str, Any] = {"limit": query.page_size, "offset": offset}
    expanding_params: list = []

    if query.search:
        where_clauses.append("""
            (
                cn.value ILIKE :search
                OR bp.product_code ILIKE :search
                OR bp.mm_number ILIKE :search
                OR bp.ta_number ILIKE :search
                OR bp.pba_number ILIKE :search
                OR bp.as_number ILIKE :search
                OR sa.name ILIKE :search
                OR EXISTS (
                    SELECT 1
                    FROM build_plan_build_notes bpbn_search
                    JOIN build_notes bn_search
                        ON bn_search.id = bpbn_search.build_note_id
                    WHERE bpbn_search.build_plan_id = bp.id
                    AND bn_search.notes ILIKE :search
                )
                OR bp.status::text ILIKE :search
                OR bpd.description ILIKE :search
                OR f.code ILIKE :search
                OR s.name ILIKE :search
            )
        """)
        params["search"] = f"%{query.search}%"

    if query.my_plans:
        access_filter = (
            "AND bpa.access_type = 'owner'"
            if query.owner_only
            else "AND bpa.access_type IN ('owner', 'editor')"
        )
        override_filter = (
            "AND bpao.access_type = 'owner'"
            if query.owner_only
            else "AND bpao.access_type IN ('owner', 'editor')"
        )
        where_clauses.append(f"""
            (
                EXISTS (
                    SELECT 1
                    FROM build_plan_access bpa
                    WHERE bpa.family_form_factor_id = bp.family_form_factor_id
                    AND bpa.user_id = :current_user_id
                    {access_filter}
                )
                OR EXISTS (
                    SELECT 1
                    FROM build_plan_access_overrides bpao
                    WHERE bpao.build_plan_id = bp.id
                    AND bpao.user_id = :current_user_id
                    {override_filter}
                )
            )
        """)
        params["current_user_id"] = current_user_id

    multi_filter_map = {
        "family_code_values": ("f.code", query.family_code, False),
        "form_factor_values": ("s.name", query.form_factor, False),
        "status_values": ("LOWER(bp.status::text)", query.status, True),
        "support_activity_values": ("LOWER(sa.name)", query.support_activity, True),
        "year_values": ("bp.year::text", query.year, False),
    }

    for param_name, (column, raw_value, normalize_lower) in multi_filter_map.items():
        values = split_values(raw_value)
        if normalize_lower:
            values = [v.lower() for v in values]
        if values:
            where_clauses.append(f"{column} IN :{param_name}")
            params[param_name] = values
            expanding_params.append(bindparam(param_name, expanding=True))

    if query.is_imported is not None:
        where_clauses.append("bp.is_imported = :is_imported")
        params["is_imported"] = bool(query.is_imported)

    column_search_map = {
        "config_number": "cn.value",
        "build_description": "bpd.description",
        "product_code": "bp.product_code",
        "mm_number": "bp.mm_number",
        "ta_number": "bp.ta_number",
        "pba_number": "bp.pba_number",
        "as_number": "bp.as_number",
    }

    for field, column in column_search_map.items():
        value = getattr(query, field)
        if not value:
            continue
        values = split_values(value)
        if len(values) > 1:
            param_name = f"{field}_values"
            where_clauses.append(f"{column} IN :{param_name}")
            params[param_name] = values
            expanding_params.append(bindparam(param_name, expanding=True))
        else:
            where_clauses.append(f"{column} ILIKE :{field}")
            params[field] = f"%{value}%"

    if query.build_notes:
        values = split_values(query.build_notes)
        if len(values) > 1:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM build_plan_build_notes bpbn_filter
                    JOIN build_notes bn_filter
                        ON bn_filter.id = bpbn_filter.build_note_id
                    WHERE bpbn_filter.build_plan_id = bp.id
                    AND bn_filter.notes IN :build_notes_values
                )
            """)
            params["build_notes_values"] = values
            expanding_params.append(bindparam("build_notes_values", expanding=True))
        else:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM build_plan_build_notes bpbn_filter
                    JOIN build_notes bn_filter
                        ON bn_filter.id = bpbn_filter.build_note_id
                    WHERE bpbn_filter.build_plan_id = bp.id
                    AND bn_filter.notes ILIKE :build_notes
                )
            """)
            params["build_notes"] = f"%{query.build_notes}%"

    if query.silicon_stepping:
        values = split_values(query.silicon_stepping)
        if len(values) > 1:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM build_plan_silicon_steppings bpss_filter
                    JOIN silicon_steppings ss_filter
                        ON ss_filter.id = bpss_filter.silicon_stepping_id
                    WHERE bpss_filter.build_plan_id = bp.id
                    AND ss_filter.name IN :silicon_stepping_values
                )
            """)
            params["silicon_stepping_values"] = values
            expanding_params.append(bindparam("silicon_stepping_values", expanding=True))
        else:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM build_plan_silicon_steppings bpss_filter
                    JOIN silicon_steppings ss_filter
                        ON ss_filter.id = bpss_filter.silicon_stepping_id
                    WHERE bpss_filter.build_plan_id = bp.id
                    AND ss_filter.name ILIKE :silicon_stepping
                )
            """)
            params["silicon_stepping"] = f"%{query.silicon_stepping}%"

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sort_pairs = parse_sort_pairs(query.sort_by, query.sort_order)
    order_by_parts = [
        f"{SORT_COLUMNS[sort_field]} {'ASC' if sort_dir == SortOrder.asc else 'DESC'}"
        for sort_field, sort_dir in sort_pairs
    ]
    if not any(part.startswith("bp.id ") for part in order_by_parts):
        order_by_parts.append("bp.id DESC")
    order_by_sql = ", ".join(order_by_parts)

    count_sql = text(f"""
        SELECT COUNT(DISTINCT bp.id)
        FROM build_plans bp
        LEFT JOIN family_form_factors fs ON fs.id = bp.family_form_factor_id
        LEFT JOIN families f ON f.id = fs.family_id
        LEFT JOIN form_factors s ON s.id = fs.form_factor_id
        LEFT JOIN build_plan_build_descs bpd ON bpd.id = bp.build_description_id
        LEFT JOIN support_activities sa ON sa.id = bp.support_activity_id
        LEFT JOIN config_numbers cn ON cn.id = bp.config_number_id
        {where_sql}
    """)
    if expanding_params:
        count_sql = count_sql.bindparams(*expanding_params)
    total = db.execute(count_sql, params).scalar() or 0

    build_plan_sql = text(f"""
        SELECT
            bp.id AS build_plan_id,
            f.code AS family_code,
            s.name AS form_factor,
            sa.name AS support_activity,
            bp.status,
            bpd.description AS build_description,
            COALESCE(
                ARRAY_AGG(DISTINCT bn.notes ORDER BY bn.notes)
                    FILTER (WHERE bn.notes IS NOT NULL),
                '{{}}'
            ) AS build_notes,
            cn.value AS config_number,
            latest_rev.revision_number AS revision,
            bp.product_code,
            bp.mm_number,
            bp.ta_number,
            bp.pba_number,
            bp.as_number,
            bp.special_instruction,
            bp.build_start_date,
            bp.ship_date,
            bp.required_quantity,
            bp.estimated_yield,
            bp.year,
            bp.is_imported,
            COALESCE(
                ARRAY_AGG(DISTINCT ss.name ORDER BY ss.name)
                    FILTER (WHERE ss.name IS NOT NULL),
                '{{}}'
            ) AS silicon_steppings
        FROM build_plans bp
        LEFT JOIN family_form_factors fs ON fs.id = bp.family_form_factor_id
        LEFT JOIN families f ON f.id = fs.family_id
        LEFT JOIN form_factors s ON s.id = fs.form_factor_id
        LEFT JOIN support_activities sa ON sa.id = bp.support_activity_id
        LEFT JOIN build_plan_build_descs bpd ON bpd.id = bp.build_description_id
        LEFT JOIN build_plan_build_notes bpbn ON bpbn.build_plan_id = bp.id
        LEFT JOIN build_notes bn ON bn.id = bpbn.build_note_id
        LEFT JOIN config_numbers cn ON cn.id = bp.config_number_id
        LEFT JOIN build_plan_revisions latest_rev ON latest_rev.id = bp.latest_revision_id
        LEFT JOIN build_plan_silicon_steppings bpss ON bpss.build_plan_id = bp.id
        LEFT JOIN silicon_steppings ss ON ss.id = bpss.silicon_stepping_id
        {where_sql}
        GROUP BY
            bp.id, f.code, s.name, sa.name, bp.status, bpd.description, cn.value,
            latest_rev.revision_number
        ORDER BY {order_by_sql}
        LIMIT :limit OFFSET :offset
    """)
    if expanding_params:
        build_plan_sql = build_plan_sql.bindparams(*expanding_params)

    build_plan_rows = db.execute(build_plan_sql, params).mappings().all()
    build_plan_ids = [row["build_plan_id"] for row in build_plan_rows]

    total_pages = (total + query.page_size - 1) // query.page_size
    pagination = {
        "page": query.page,
        "page_size": query.page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": query.page < total_pages,
        "has_prev": query.page > 1,
    }
    sorting = {"sort_by": query.sort_by, "sort_order": query.sort_order}
    filters = {
        "search": query.search,
        "family_code": query.family_code,
        "form_factor": query.form_factor,
        "status": query.status,
        "support_activity": query.support_activity,
    }

    if not build_plan_ids:
        return {
            "data": [],
            "pagination": pagination,
            "sorting": sorting,
            "filters": filters,
        }

    components = _fetch_components(db, build_plan_ids)
    tests = _fetch_tests(db, build_plan_ids)
    orders = _fetch_orders(db, build_plan_ids)
    recipients = _fetch_recipients(db, build_plan_ids)
    warehouses = _fetch_warehouses_multi(db, build_plan_ids)
    shipments = _fetch_shipments_multi(db, build_plan_ids)

    components_by_plan: dict[int, list[dict]] = defaultdict(list)
    for c in components:
        components_by_plan[c["build_plan_id"]].append({
            "component_name": c["component_name"],
            "component_slot": c["component_slot"],
            "supplier": c["supplier"],
            "attributes": c["attributes"],
        })

    tests_by_plan: dict[int, list[dict]] = defaultdict(list)
    for t in tests:
        tests_by_plan[t["build_plan_id"]].append({
            "test_name": t["test_name"],
            "test_detail": t["test_detail"],
        })

    orders_by_plan: dict[int, list[dict]] = defaultdict(list)
    for o in orders:
        orders_by_plan[o["build_plan_id"]].append({
            "build_request_id": o["build_request_id"],
            "requestor_name": o["requestor_name"],
            "quantity": o["quantity"],
        })

    # Group recipient/requestor pairs by recipient user.
    recipients_by_plan: dict[int, dict[int, dict]] = defaultdict(dict)
    for r in recipients:
        bp_id = r["build_plan_id"]
        recipient_id = r["recipient_user_id"]
        key = recipient_id if recipient_id is not None else 0
        block = recipients_by_plan[bp_id].get(key)
        if block is None:
            block = {
                "recipient": {
                    "id": recipient_id,
                    "full_name": r["recipient_full_name"],
                    "email": r["recipient_email"],
                } if recipient_id is not None else None,
                "requestors": [],
            }
            recipients_by_plan[bp_id][key] = block
        block["requestors"].append({
            "name": r["requestor_full_name"],
            "user_id": r["requestor_user_id"],
            "quantity": r["quantity"],
        })

    warehouses_by_plan: dict[int, list[dict]] = defaultdict(list)
    for w in warehouses:
        warehouses_by_plan[w["build_plan_id"]].append({
            "warehouse_id": w["warehouse_id"],
            "warehouse_name": w["warehouse_name"],
            "quantity_stored": w["quantity_stored"],
        })

    shipments_by_plan: dict[int, list[dict]] = defaultdict(list)
    # Lookup: (build_plan_id, recipient_user_id) -> list of requestor dicts.
    # Used to attach the SUM-parsed recipients list onto each shipment whose
    # package recipient (``handler``) matches the build_plan_shippings
    # recipient_user.
    shipment_recipients_lookup: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in recipients:
        recipient_id = r["recipient_user_id"]
        if recipient_id is None:
            continue
        shipment_recipients_lookup[(r["build_plan_id"], recipient_id)].append({
            "name": r["requestor_full_name"],
            "user_id": r["requestor_user_id"],
            "quantity": r["quantity"],
        })

    for s in shipments:
        shipment = _shipment_dict(s)
        recipient_user_id = s["recipient_user_id"]
        if recipient_user_id is not None:
            shipment["recipients"] = shipment_recipients_lookup.get(
                (s["build_plan_id"], recipient_user_id), []
            )
        else:
            shipment["recipients"] = []
        shipments_by_plan[s["build_plan_id"]].append(shipment)

    data = []
    for row in build_plan_rows:
        bp_id = row["build_plan_id"]
        data.append({
            "build_plan_id": bp_id,
            "family_code": row["family_code"],
            "form_factor": row["form_factor"],
            "support_activity": row["support_activity"],
            "status": row["status"],
            "build_description": row["build_description"],
            "build_notes": row["build_notes"],
            "config_number": row["config_number"],
            "revision": row["revision"],
            "product_code": row["product_code"],
            "mm_number": row["mm_number"],
            "ta_number": row["ta_number"],
            "pba_number": row["pba_number"],
            "as_number": row["as_number"],
            "special_instruction": row["special_instruction"],
            "build_start_date": row["build_start_date"],
            "ship_date": row["ship_date"],
            "required_quantity": row["required_quantity"],
            "estimated_yield": row["estimated_yield"],
            "year": row["year"],
            "silicon_steppings": row["silicon_steppings"] or [],
            "is_imported": bool(row["is_imported"]),
            "components": components_by_plan[bp_id],
            "tests": tests_by_plan[bp_id],
            "build_requests": orders_by_plan[bp_id],
            "recipients": list(recipients_by_plan[bp_id].values()),
            "warehouses": warehouses_by_plan[bp_id],
            "shipments": shipments_by_plan[bp_id],
        })

    return {
        "data": data,
        "pagination": pagination,
        "sorting": sorting,
        "filters": filters,
    }


def get_filter_options(db: Session) -> dict[str, Any]:
    sql = text("""
        SELECT
            COALESCE(
                ARRAY_AGG(DISTINCT f.code ORDER BY f.code)
                    FILTER (WHERE f.code IS NOT NULL),
                '{}'
            ) AS family_code,
            COALESCE(
                ARRAY_AGG(DISTINCT s.name ORDER BY s.name)
                    FILTER (WHERE s.name IS NOT NULL),
                '{}'
            ) AS form_factor,
            COALESCE(
                ARRAY_AGG(DISTINCT sa.name ORDER BY sa.name)
                    FILTER (WHERE sa.name IS NOT NULL),
                '{}'
            ) AS support_activity,
            COALESCE(
                ARRAY_AGG(DISTINCT bpd.description ORDER BY bpd.description)
                    FILTER (WHERE bpd.description IS NOT NULL),
                '{}'
            ) AS build_description,
            COALESCE(
                ARRAY_AGG(DISTINCT bn.notes ORDER BY bn.notes)
                    FILTER (WHERE bn.notes IS NOT NULL),
                '{}'
            ) AS build_notes,
            COALESCE(
                ARRAY_AGG(DISTINCT bp.year::text ORDER BY bp.year::text)
                    FILTER (WHERE bp.year IS NOT NULL),
                '{}'
            ) AS year,
            COALESCE(
                ARRAY_AGG(DISTINCT ss.name ORDER BY ss.name)
                    FILTER (WHERE ss.name IS NOT NULL),
                '{}'
            ) AS silicon_stepping
        FROM build_plans bp
        LEFT JOIN family_form_factors fs ON fs.id = bp.family_form_factor_id
        LEFT JOIN families f ON f.id = fs.family_id
        LEFT JOIN form_factors s ON s.id = fs.form_factor_id
        LEFT JOIN support_activities sa ON sa.id = bp.support_activity_id
        LEFT JOIN build_plan_build_descs bpd ON bpd.id = bp.build_description_id
        LEFT JOIN build_plan_build_notes bpbn ON bpbn.build_plan_id = bp.id
        LEFT JOIN build_notes bn ON bn.id = bpbn.build_note_id
        LEFT JOIN build_plan_silicon_steppings bpss ON bpss.build_plan_id = bp.id
        LEFT JOIN silicon_steppings ss ON ss.id = bpss.silicon_stepping_id
    """)
    row = db.execute(sql).mappings().first()
    return {
        "family_code": row["family_code"] or [],
        "form_factor": row["form_factor"] or [],
        "support_activity": row["support_activity"] or [],
        "build_description": row["build_description"] or [],
        "build_notes": row["build_notes"] or [],
        "year": row["year"] or [],
        "silicon_stepping": row["silicon_stepping"] or [],
        "status": ["Plan", "Hold", "Done", "Cancelled", "New"],
    }


def get_build_plan_by_id(db: Session, build_plan_id: int) -> dict[str, Any] | None:
    build_plan_sql = text("""
        SELECT
            bp.id AS build_plan_id,
            f.code AS family_code,
            s.name AS form_factor,
            sa.name AS support_activity,
            bp.status,
            bpd.description AS build_description,
            COALESCE(
                ARRAY_AGG(DISTINCT bn.notes ORDER BY bn.notes)
                    FILTER (WHERE bn.notes IS NOT NULL),
                '{}'
            ) AS build_notes,
            cn.value AS config_number,
            latest_rev.revision_number AS revision,
            bp.product_code,
            bp.mm_number,
            bp.ta_number,
            bp.pba_number,
            bp.as_number,
            bp.special_instruction,
            bp.build_start_date,
            bp.ship_date,
            bp.required_quantity,
            bp.estimated_yield,
            bp.year,
            bp.is_imported,
            COALESCE(
                ARRAY_AGG(DISTINCT ss.name ORDER BY ss.name)
                    FILTER (WHERE ss.name IS NOT NULL),
                '{}'
            ) AS silicon_steppings
        FROM build_plans bp
        LEFT JOIN family_form_factors fs ON fs.id = bp.family_form_factor_id
        LEFT JOIN families f ON f.id = fs.family_id
        LEFT JOIN form_factors s ON s.id = fs.form_factor_id
        LEFT JOIN support_activities sa ON sa.id = bp.support_activity_id
        LEFT JOIN build_plan_build_descs bpd ON bpd.id = bp.build_description_id
        LEFT JOIN build_plan_build_notes bpbn ON bpbn.build_plan_id = bp.id
        LEFT JOIN build_notes bn ON bn.id = bpbn.build_note_id
        LEFT JOIN config_numbers cn ON cn.id = bp.config_number_id
        LEFT JOIN build_plan_revisions latest_rev ON latest_rev.id = bp.latest_revision_id
        LEFT JOIN build_plan_silicon_steppings bpss ON bpss.build_plan_id = bp.id
        LEFT JOIN silicon_steppings ss ON ss.id = bpss.silicon_stepping_id
        WHERE bp.id = :build_plan_id
        GROUP BY
            bp.id, f.code, s.name, sa.name, bp.status, bpd.description, cn.value,
            latest_rev.revision_number
    """)
    row = db.execute(build_plan_sql, {"build_plan_id": build_plan_id}).mappings().first()
    if not row:
        return None

    components = _fetch_components(db, [build_plan_id])
    tests = _fetch_tests(db, [build_plan_id])
    orders = _fetch_orders(db, [build_plan_id])
    recipient_rows = _fetch_recipients(db, [build_plan_id])

    warehouse_sql = text("""
        SELECT
            w.id AS warehouse_id,
            w.name AS warehouse_name,
            COALESCE(q.quantity_stored, 0) AS quantity_stored
        FROM warehouses w
        LEFT JOIN quantity_stored_in_warehouse q
            ON q.buildplan_id = :build_plan_id
           AND q.warehouse_id = w.id
        ORDER BY w.id
    """)
    warehouse_rows = db.execute(warehouse_sql, {"build_plan_id": build_plan_id}).mappings().all()

    shipment_sql = text("""
        SELECT
            sh.id AS shipment_id,
            cn.value AS config_number,
            sh.tracking_number,
            f.name AS forwarder,
            sh.quantity,
            sh.comments,
            sh.ship_date,
            sh.eta,
            sh.delivery_date,
            sh.status,
            recipient.id AS recipient_user_id,
            recipient.full_name AS recipient_full_name,
            recipient.email AS recipient_email,
            recipient.full_name AS handler_name
        FROM shippings sh
        JOIN config_numbers cn ON cn.id = sh.config_number_id
        JOIN build_plans bp ON bp.config_number_id = cn.id
        LEFT JOIN users recipient ON recipient.id = sh.recipient_user_id
        LEFT JOIN forwarders f ON f.id = sh.forwarder_id
        WHERE bp.id = :build_plan_id
        ORDER BY sh.ship_date DESC, sh.id DESC
    """)
    shipment_rows = db.execute(shipment_sql, {"build_plan_id": build_plan_id}).mappings().all()

    # The build-request requestor user IDs for this plan; recipients on the
    # Shipments tab should be limited to users who actually filed a build
    # request for this build.
    request_requestor_ids: set[int] = {
        o["requestor_user_id"]
        for o in orders
        if o.get("requestor_user_id") is not None
    }

    # Group SUM-parsed requestors by recipient user so we can attach them to
    # each shipment whose package recipient matches.
    shipment_recipients_lookup: dict[int, list[dict]] = defaultdict(list)
    for r in recipient_rows:
        recipient_id = r["recipient_user_id"]
        if recipient_id is None:
            continue
        requestor_id = r["requestor_user_id"]
        if requestor_id is None or requestor_id not in request_requestor_ids:
            continue
        shipment_recipients_lookup[recipient_id].append({
            "name": r["requestor_full_name"],
            "user_id": requestor_id,
            "quantity": r["quantity"],
        })

    shipments_out: list[dict] = []
    for s in shipment_rows:
        ship = _shipment_dict(dict(s))
        ship["recipients"] = shipment_recipients_lookup.get(
            s["recipient_user_id"], []
        ) if s["recipient_user_id"] is not None else []
        shipments_out.append(ship)

    return {
        "build_plan_id": row["build_plan_id"],
        "family_code": row["family_code"],
        "form_factor": row["form_factor"],
        "support_activity": row["support_activity"],
        "status": row["status"],
        "build_description": row["build_description"],
        "build_notes": row["build_notes"],
        "config_number": row["config_number"],
        "revision": row["revision"],
        "product_code": row["product_code"],
        "mm_number": row["mm_number"],
        "ta_number": row["ta_number"],
        "pba_number": row["pba_number"],
        "as_number": row["as_number"],
        "special_instruction": row["special_instruction"],
        "build_start_date": row["build_start_date"],
        "ship_date": row["ship_date"],
        "required_quantity": row["required_quantity"],
        "estimated_yield": row["estimated_yield"],
        "year": row["year"],
        "silicon_steppings": row["silicon_steppings"] or [],
        "is_imported": bool(row["is_imported"]),
        "components": [
            {
                "component_name": c["component_name"],
                "component_slot": c["component_slot"],
                "supplier": c["supplier"],
                "attributes": c["attributes"],
            }
            for c in components
        ],
        "tests": [
            {"test_name": t["test_name"], "test_detail": t["test_detail"]}
            for t in tests
        ],
        "build_requests": [
            {
                "build_request_id": o["build_request_id"],
                "requestor_name": o["requestor_name"],
                "quantity": o["quantity"],
            }
            for o in orders
        ],
        "recipients": _group_recipients(recipient_rows),
        "warehouses": [dict(w) for w in warehouse_rows],
        "shipments": shipments_out,
    }


def get_build_plan_revisions(db: Session, build_plan_id: int) -> dict[str, Any] | None:
    """Return the revision history for a canonical build plan.

    Each row corresponds to one entry in ``build_plan_revisions``, ordered
    newest first. The revision-aware import flow (see
    ``db/bulk_import_pseudocode.md``) appends one row per real change; files
    that did not change anything are listed under ``touches`` instead.
    """
    target = db.execute(
        text(
            """
            SELECT bp.id, bp.config_number_id,
                   cn.value AS config_number,
                   f.code AS family_code,
                   s.name AS form_factor
            FROM build_plans bp
            LEFT JOIN config_numbers cn ON cn.id = bp.config_number_id
            LEFT JOIN family_form_factors fs ON fs.id = bp.family_form_factor_id
            LEFT JOIN families f ON f.id = fs.family_id
            LEFT JOIN form_factors s ON s.id = fs.form_factor_id
            WHERE bp.id = :id
            """
        ),
        {"id": build_plan_id},
    ).mappings().first()
    if not target:
        return None

    revisions = db.execute(
        text(
            """
            SELECT
                rev.id AS revision_id,
                rev.revision_number,
                rev.work_year,
                rev.work_week,
                rev.file_revision,
                rev.status_at_revision AS status,
                rev.changed_fields,
                rev.snapshot,
                rev.is_imported,
                rev.created_at,
                imp.id AS import_file_id,
                imp.original_filename AS import_file_name,
                imp.work_year AS import_file_work_year,
                imp.work_week AS import_file_work_week,
                imp.file_revision AS import_file_revision
            FROM build_plan_revisions rev
            LEFT JOIN build_plan_import_files imp ON imp.id = rev.import_file_id
            WHERE rev.build_plan_id = :id
            ORDER BY rev.revision_number DESC
            """
        ),
        {"id": build_plan_id},
    ).mappings().all()

    touches = db.execute(
        text(
            """
            SELECT
                t.id AS touch_id,
                t.matched_revision_id,
                t.created_at,
                imp.id AS import_file_id,
                imp.original_filename AS import_file_name,
                imp.work_year,
                imp.work_week,
                imp.file_revision
            FROM build_plan_import_file_touches t
            JOIN build_plan_import_files imp ON imp.id = t.import_file_id
            WHERE t.build_plan_id = :id
            ORDER BY imp.work_year DESC NULLS LAST,
                     imp.work_week DESC NULLS LAST,
                     imp.file_revision DESC NULLS LAST,
                     t.created_at DESC
            """
        ),
        {"id": build_plan_id},
    ).mappings().all()

    # Build a per-build-plan map: requester full_name -> recipient user
    # full_name, using ``build_plan_shippings``. Older revision snapshots
    # may pre-date the recipient/requestor refactor, so we enrich them on
    # the fly for UI grouping. Snapshots themselves are never mutated.
    revisions_out: list[dict] = []
    requester_names: set[str] = set()
    for r in revisions:
        snap = r.get("snapshot") or {}
        for row in snap.get("build_requests") or []:
            name = (row.get("requester") or "").strip()
            if name:
                requester_names.add(name)

    requester_to_recipient: dict[str, str | None] = {}
    if requester_names:
        rows = db.execute(
            text(
                """
                SELECT requestor.full_name AS requestor_name,
                       recipient.full_name AS recipient_name
                FROM build_plan_shippings bps
                JOIN users requestor ON requestor.id = bps.requestor_user_id
                LEFT JOIN users recipient ON recipient.id = bps.recipient_user_id
                WHERE bps.build_plan_id = :build_plan_id
                  AND requestor.full_name = ANY(:names)
                """
            ),
            {
                "build_plan_id": build_plan_id,
                "names": list(requester_names),
            },
        ).mappings().all()
        for row in rows:
            requester_to_recipient[row["requestor_name"]] = row["recipient_name"]

    for r in revisions:
        r_dict = dict(r)
        snap = r_dict.get("snapshot")
        if isinstance(snap, dict):
            enriched_snap = dict(snap)
            enriched_orders = []
            for row in snap.get("build_requests") or []:
                row_copy = dict(row)
                name = (row_copy.get("requester") or "").strip()
                if not row_copy.get("recipient") and name in requester_to_recipient:
                    row_copy["recipient"] = requester_to_recipient[name]
                enriched_orders.append(row_copy)
            enriched_snap["build_requests"] = enriched_orders
            r_dict["snapshot"] = enriched_snap
        revisions_out.append(r_dict)

    return {
        "build_plan_id": build_plan_id,
        "config_number_id": target["config_number_id"],
        "config_number": target["config_number"],
        "family_code": target["family_code"],
        "form_factor": target["form_factor"],
        "revisions": revisions_out,
        "touches": [dict(t) for t in touches],
    }
