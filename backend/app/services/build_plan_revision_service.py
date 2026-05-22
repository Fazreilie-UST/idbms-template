"""Snapshot, diff, and case-A/B/C processing for the revision-aware build
plan import flow. See ``db/bulk_import_pseudocode.md`` for the design."""

from __future__ import annotations

import math
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.build.build_plan import BuildPlan, BuildPlanStatus
from app.models.build.build_plan_component import BuildPlanComponent
from app.models.build.build_plan_test import BuildPlanTest
from app.models.build.build_plan_build_request import BuildPlanBuildRequest
from app.models.build.warehouse import QuantityStoredInWarehouse
from app.models.build.build_plan_import_file import BuildPlanImportFile
from app.models.build.build_plan_revision import BuildPlanRevision
from app.models.build.build_plan_import_file_touch import BuildPlanImportFileTouch
from app.models.build.family_form_factor import FamilyFormFactor
from app.models.build.silicon_stepping import BuildPlanSiliconStepping


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class StatusRegressionError(ValueError):
    """Raised when an incoming latest-wins revision would move the canonical
    status backwards along the allowed transition order."""


# ---------------------------------------------------------------------------
# Status monotonicity
# ---------------------------------------------------------------------------

# Allowed transition order (per pseudocode):
#   New < Plan < Hold < Done
#                     < Cancelled
# Hold ↔ Plan are both fine; Done / Cancelled are terminal.
_STATUS_RANK = {
    BuildPlanStatus.new: 0,
    BuildPlanStatus.plan: 1,
    BuildPlanStatus.hold: 2,
    BuildPlanStatus.done: 3,
    BuildPlanStatus.cancelled: 3,
}


def violates_monotonic_order(old: BuildPlanStatus, new: BuildPlanStatus) -> bool:
    if old == new:
        return False
    # Done / Cancelled are terminal -> any move off them is a regression.
    if old in (BuildPlanStatus.done, BuildPlanStatus.cancelled):
        return True
    return False


# ---------------------------------------------------------------------------
# Snapshot construction (from parsed Excel column)
# ---------------------------------------------------------------------------

def _clean(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _safe_int(value: Any) -> int | None:
    """Parse a cell value as an integer, truncating any fractional part.

    Excel cells holding a formula result (e.g. ``=A/B``) are delivered to
    pandas/openpyxl as floats like ``36.666666666666664``. We must parse
    via ``float`` first; stripping non-digits would turn that into the
    17-digit integer ``36666666666666664``.
    """
    s = _clean(value)
    if s is None:
        return None
    # Drop thousands separators / stray whitespace but keep the decimal point.
    s = s.replace(",", "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _safe_int_ceil(value: Any) -> int | None:
    """Same as :func:`_safe_int` but rounds *up* (ceiling).

    Used for quantities like ``Build Start Quantity`` which are often the
    result of ``required_quantity / yield`` in Excel and need to round up
    so all required units are covered (e.g. 33 / 0.90 -> 37, not 36).
    """
    s = _clean(value)
    if s is None:
        return None
    s = s.replace(",", "").strip()
    if not s:
        return None
    try:
        return math.ceil(float(s))
    except ValueError:
        return None


def _safe_percent_int(value: Any) -> int | None:
    s = _clean(value)
    if s is None:
        return None
    s = s.replace("%", "").strip()
    try:
        number = float(s)
    except ValueError:
        return None
    # Excel percentage cells deliver 90% as 0.9 and 100% as 1.0.
    # Treat any value in (0, 1] as a fractional percent and scale up.
    if 0 < number <= 1:
        number = number * 100
    return int(round(number))


def _split_build_notes(value: Any) -> list[str]:
    s = _clean(value)
    if not s:
        return []
    s = s.replace("\uFF0C", ",")
    return sorted(
        {n.strip() for n in re.split(r"[,;\n]+", s) if n.strip()}
    )


def _normalise_status(value: Any) -> str:
    """Return the snapshot string for status. Mirrors map_build_status but
    deterministic — used so two snapshots compare equal."""
    s = _clean(value)
    if not s:
        return BuildPlanStatus.new.value
    s_low = s.lower()
    for member in BuildPlanStatus:
        if member.value.lower() == s_low or member.name.lower() == s_low:
            return member.value
    if s_low in ("planning",):
        return BuildPlanStatus.plan.value
    if s_low in ("on hold",):
        return BuildPlanStatus.hold.value
    if s_low in ("complete", "completed", "finished"):
        return BuildPlanStatus.done.value
    if s_low in ("cancel", "canceled"):
        return BuildPlanStatus.cancelled.value
    return BuildPlanStatus.new.value


def build_snapshot(parsed_column: dict[str, Any]) -> dict[str, Any]:
    """Convert a parsed Excel column into the canonical snapshot shape.

    The snapshot is intentionally normalised (sorted lists, cleaned strings,
    ints rather than raw text) so that two snapshots produced from equivalent
    source data compare equal under :func:`diff_snapshot`.
    """
    build_info = parsed_column.get("build_info", {}) or {}
    quantities = parsed_column.get("quantities", {}) or {}
    key_components = parsed_column.get("key_components", {}) or {}
    test_section = parsed_column.get("test_section", {}) or {}
    samples = parsed_column.get("samples", []) or []
    warehouse_quantities = parsed_column.get("warehouse_quantities", {}) or {}

    config_number_raw = _clean(build_info.get("Config Number"))
    derived_year: int | None = None
    derived_work_week: int | None = None
    if config_number_raw:
        m = re.search(r"[A-Za-z](\d{2})(\d{2})", config_number_raw)
        if m:
            derived_year = 2000 + int(m.group(1))
            ww = int(m.group(2))
            if 1 <= ww <= 53:
                derived_work_week = ww

    # Silicon stepping: split on whitespace/comma/semicolon/slash, dedupe,
    # sort so two snapshots with the same set compare equal.
    raw_si = None
    for k, v in key_components.items():
        if (_clean(k) or "") == "Silicon Stepping":
            raw_si = v
            break
    silicon_steppings = sorted({
        t.strip()
        for t in re.split(r"[\s,;/]+", _clean(raw_si) or "")
        if t.strip()
    })

    plan = {
        "status": _normalise_status(build_info.get("Status")),
        "support_activity": _clean(build_info.get("Support Activity")) or "Integration",
        "build_description": _clean(build_info.get("Build Description")) or "N/A",
        "product_code": _clean(build_info.get("Product Code")),
        "mm_number": _clean(build_info.get("MM Number")),
        "ta_number": _clean(build_info.get("TA Number")) or "N/A",
        "pba_number": _clean(build_info.get("PBA Number")),
        "as_number": _clean(build_info.get("AS Number")),
        "special_instruction": _clean(build_info.get("Special Instruction")),
        "required_quantity": _safe_int(quantities.get("Required Quantity")),
        "estimated_yield": _safe_percent_int(quantities.get("Estimated Yield")),
        "build_start_quantity": _safe_int_ceil(quantities.get("Build Start Quantity")),
        "build_notes": _split_build_notes(build_info.get("Build Notes")),
        "year": derived_year,
        "work_week": derived_work_week,
        "silicon_steppings": silicon_steppings,
    }

    # Guard PostgreSQL INTEGER range (-2,147,483,648 .. 2,147,483,647).
    # Without this a broken Excel formula (e.g. build_start_quantity coming
    # in as 3.67e16) surfaces as an anonymous NumericValueOutOfRange at
    # commit time with no Config Number context.
    _PG_INT_MAX = 2_147_483_647
    _PG_INT_MIN = -2_147_483_648
    for _field_label, _field_key in (
        ("Required Quantity", "required_quantity"),
        ("Estimated Yield", "estimated_yield"),
        ("Build Start Quantity", "build_start_quantity"),
    ):
        _v = plan[_field_key]
        if _v is None:
            continue
        if _v < _PG_INT_MIN or _v > _PG_INT_MAX:
            raise ValueError(
                f"Config {config_number_raw or '(unknown)'}: "
                f"{_field_label}={_v!r} is out of INTEGER range. "
                "Check the corresponding cell in the Excel file "
                "(likely a broken formula)."
            )

    components = sorted(
        (
            {"field": _clean(k), "value": _clean(v)}
            for k, v in key_components.items()
            if _clean(v) and (_clean(k) or "") != "Silicon Stepping"
        ),
        key=lambda r: (r["field"] or "", r["value"] or ""),
    )

    tests = sorted(
        (
            {"field": _clean(k), "value": _clean(v)}
            for k, v in test_section.items()
            if _clean(v)
        ),
        key=lambda r: (r["field"] or "", r["value"] or ""),
    )

    # Per spec: build request equality = (requester, recipient, quantity).
    # We don't know the recipient from the raw sample row alone, so it's
    # carried as None; diff comparison is still correct because both sides
    # use the same shape.
    build_requests_seen: dict[tuple[str | None, str | None], int] = {}
    for entry in samples:
        # Sample rows are emitted by the parser as dicts
        # ``{"name", "value", "is_bold", "formula_refs", "row_idx"}``;
        # accept legacy 3-tuples and 2-tuples as well.
        if isinstance(entry, dict):
            raw_name = entry.get("name")
            raw_qty = entry.get("value")
        elif len(entry) == 3:
            raw_name, raw_qty, _is_bold = entry
        else:
            raw_name, raw_qty = entry
        name = _clean(raw_name)
        if not name:
            continue
        qty = _safe_int(raw_qty)
        if qty is None or qty <= 0:
            continue
        key = (name, None)
        build_requests_seen[key] = qty
    build_requests = sorted(
        (
            {"requester": k[0], "recipient": k[1], "quantity": q}
            for k, q in build_requests_seen.items()
        ),
        key=lambda r: (r["requester"] or "", r["recipient"] or ""),
    )

    warehouse = sorted(
        (
            {"warehouse": _clean(name), "quantity": _safe_int(qty)}
            for name, qty in warehouse_quantities.items()
            if _safe_int(qty) is not None
        ),
        key=lambda r: r["warehouse"] or "",
    )

    return {
        "plan": plan,
        "components": components,
        "tests": tests,
        "build_requests": build_requests,
        "warehouse_quantities": warehouse,
    }


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def _diff_plan(old: dict, new: dict) -> dict:
    out: dict[str, Any] = {}
    for key in set(old) | set(new):
        if old.get(key) != new.get(key):
            out[key] = [old.get(key), new.get(key)]
    return out


def _row_key(row: dict, key_fields: tuple[str, ...]) -> tuple:
    return tuple(row.get(f) for f in key_fields)


def _diff_rows(old: list[dict], new: list[dict], key_fields: tuple[str, ...]) -> dict:
    """Row-level diff. Equality of rows is by *all* fields. Identity for the
    add/remove/changed split is by ``key_fields``."""
    old_by_key = {_row_key(r, key_fields): r for r in old}
    new_by_key = {_row_key(r, key_fields): r for r in new}

    added = [new_by_key[k] for k in new_by_key.keys() - old_by_key.keys()]
    removed = [old_by_key[k] for k in old_by_key.keys() - new_by_key.keys()]
    changed = [
        {"key": list(k), "before": old_by_key[k], "after": new_by_key[k]}
        for k in old_by_key.keys() & new_by_key.keys()
        if old_by_key[k] != new_by_key[k]
    ]
    if not added and not removed and not changed:
        return {}
    return {"added": added, "removed": removed, "changed": changed}


def diff_snapshot(old: dict, new: dict) -> dict:
    """Return ``{}`` iff snapshots are equal, otherwise a structured diff."""
    out: dict[str, Any] = {}

    plan_diff = _diff_plan(old.get("plan", {}), new.get("plan", {}))
    if plan_diff:
        out["plan"] = plan_diff

    for section, key_fields in (
        ("components", ("field",)),
        ("tests", ("field",)),
        ("build_requests", ("requester", "recipient")),
        ("warehouse_quantities", ("warehouse",)),
    ):
        rows_diff = _diff_rows(old.get(section, []), new.get(section, []), key_fields)
        if rows_diff:
            out[section] = rows_diff

    return out


# ---------------------------------------------------------------------------
# Revision row helpers
# ---------------------------------------------------------------------------

def _chrono_key(rev: BuildPlanRevision) -> tuple:
    """Sort key for revisions. NULLs sort last by treating None as +inf."""
    return (
        rev.work_year if rev.work_year is not None else 9_999,
        rev.work_week if rev.work_week is not None else 99,
        rev.file_revision if rev.file_revision is not None else 9_999,
        rev.id or 0,
    )


def _shift_revision_numbers(
    session: Session,
    build_plan_id: int,
    start_at: int,
    by: int,
) -> None:
    """Bump every revision_number >= start_at by ``by``. Done in two passes
    via a negative placeholder so the unique (build_plan_id, revision_number)
    constraint is never violated mid-update."""
    revs = (
        session.query(BuildPlanRevision)
        .filter(
            BuildPlanRevision.build_plan_id == build_plan_id,
            BuildPlanRevision.revision_number >= start_at,
        )
        .order_by(BuildPlanRevision.revision_number.desc())
        .all()
    )
    for r in revs:
        r.revision_number = -r.revision_number
    session.flush()
    for r in revs:
        r.revision_number = (-r.revision_number) + by
    session.flush()


def _record_touch(
    session: Session,
    import_file: BuildPlanImportFile,
    build_plan: BuildPlan,
    matched_revision: BuildPlanRevision | None,
) -> None:
    matched_id = matched_revision.id if matched_revision else None

    # Check pending (not-yet-flushed) touches first so multiple columns in
    # the same import file that resolve to the same build plan don't try to
    # insert duplicate (import_file_id, build_plan_id) rows in one flush.
    for pending in session.new:
        if (
            isinstance(pending, BuildPlanImportFileTouch)
            and pending.import_file_id == import_file.id
            and pending.build_plan_id == build_plan.id
        ):
            pending.matched_revision_id = matched_id
            return

    existing = (
        session.query(BuildPlanImportFileTouch)
        .filter_by(
            import_file_id=import_file.id,
            build_plan_id=build_plan.id,
        )
        .first()
    )
    if existing is not None:
        existing.matched_revision_id = matched_id
        return
    session.add(
        BuildPlanImportFileTouch(
            import_file_id=import_file.id,
            build_plan_id=build_plan.id,
            matched_revision_id=matched_id,
        )
    )


def _create_revision(
    session: Session,
    build_plan: BuildPlan,
    import_file: BuildPlanImportFile,
    revision_number: int,
    snapshot: dict,
    changed_fields: dict,
) -> BuildPlanRevision:
    rev = BuildPlanRevision(
        build_plan_id=build_plan.id,
        revision_number=revision_number,
        import_file_id=import_file.id if import_file is not None else None,
        work_year=import_file.work_year if import_file is not None else None,
        work_week=import_file.work_week if import_file is not None else None,
        file_revision=import_file.file_revision if import_file is not None else None,
        snapshot=snapshot,
        changed_fields=changed_fields,
        status_at_revision=BuildPlanStatus(snapshot["plan"]["status"]),
        is_imported=import_file is not None,
    )
    session.add(rev)
    session.flush()
    return rev


# ---------------------------------------------------------------------------
# Apply / replace canonical row + children
# ---------------------------------------------------------------------------

def _apply_scalars(
    session: Session,
    build_plan: BuildPlan,
    snapshot: dict,
    *,
    support_activity_resolver,
    build_desc_resolver,
) -> None:
    """Copy plan-level scalars from snapshot onto the canonical build_plan
    row. ``*_resolver`` callables come from ``seed_build_plan`` to handle the
    FK lookups (get_or_create support activity / build description)."""
    plan = snapshot["plan"]

    support_activity = support_activity_resolver(session, plan["support_activity"])
    build_desc = build_desc_resolver(session, support_activity, plan["build_description"])

    build_plan.support_activity_id = support_activity.id
    build_plan.build_description_id = build_desc.id
    build_plan.status = BuildPlanStatus(plan["status"])
    build_plan.product_code = plan["product_code"]
    build_plan.mm_number = plan["mm_number"]
    build_plan.ta_number = plan["ta_number"]
    build_plan.pba_number = plan["pba_number"]
    build_plan.as_number = plan["as_number"]
    build_plan.special_instruction = plan["special_instruction"]
    build_plan.required_quantity = plan["required_quantity"]
    build_plan.estimated_yield = plan["estimated_yield"]
    build_plan.build_start_quantity = plan["build_start_quantity"]
    if "year" in plan:
        build_plan.year = plan["year"]
    if "work_week" in plan:
        build_plan.work_week = plan["work_week"]
    session.flush()


def _wipe_children(session: Session, build_plan: BuildPlan) -> None:
    """Remove component/test/order-link/warehouse children. Component
    attribute values cascade via the BuildPlanComponent FK."""
    session.query(BuildPlanComponent).filter_by(build_plan_id=build_plan.id).delete(
        synchronize_session=False
    )
    session.query(BuildPlanTest).filter_by(build_plan_id=build_plan.id).delete(
        synchronize_session=False
    )
    session.query(BuildPlanBuildRequest).filter_by(build_plan_id=build_plan.id).delete(
        synchronize_session=False
    )
    session.query(QuantityStoredInWarehouse).filter_by(buildplan_id=build_plan.id).delete(
        synchronize_session=False
    )
    session.query(BuildPlanSiliconStepping).filter_by(
        build_plan_id=build_plan.id
    ).delete(synchronize_session=False)
    session.flush()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def process_parsed_column(
    session: Session,
    *,
    import_file: BuildPlanImportFile,
    family_form_factor: FamilyFormFactor,
    config_number,
    parsed_column: dict[str, Any],
    summary: dict[str, Any],
    seed_helpers,
) -> None:
    """Process one parsed Excel column (one config_number) end-to-end.

    Implements CASE A / B / C from ``db/bulk_import_pseudocode.md``.
    ``seed_helpers`` is the ``app.scripts.seed_build_plan`` module — passed in
    rather than imported to avoid a circular dependency.
    """
    snapshot = build_snapshot(parsed_column)

    bp = (
        session.query(BuildPlan)
        .filter_by(
            family_form_factor_id=family_form_factor.id,
            config_number_id=config_number.id,
        )
        .first()
    )

    chrono_in = (
        import_file.work_year if import_file.work_year is not None else 9_999,
        import_file.work_week if import_file.work_week is not None else 99,
        import_file.file_revision if import_file.file_revision is not None else 9_999,
        0,
    )

    # ===================================================================
    # NEW build plan
    # ===================================================================
    if bp is None:
        bp = BuildPlan(
            family_form_factor_id=family_form_factor.id,
            config_number_id=config_number.id,
            status=BuildPlanStatus(snapshot["plan"]["status"]),
            support_activity_id=None,  # set by _apply_scalars
            build_description_id=None,
            is_imported=True,
        )
        # Need a placeholder for the NOT NULL FK fields before flush; use the
        # resolved ids from _apply_scalars.
        plan = snapshot["plan"]
        sa = seed_helpers.get_or_create_support_activity(session, plan["support_activity"])
        bd = seed_helpers.get_or_create_build_desc(session, sa, plan["build_description"])
        bp.support_activity_id = sa.id
        bp.build_description_id = bd.id
        session.add(bp)
        session.flush()

        _apply_scalars(
            session,
            bp,
            snapshot,
            support_activity_resolver=seed_helpers.get_or_create_support_activity,
            build_desc_resolver=seed_helpers.get_or_create_build_desc,
        )
        _populate_children(session, bp, family_form_factor, parsed_column, seed_helpers)
        _link_build_notes(session, bp, snapshot, seed_helpers)

        rev = _create_revision(
            session,
            bp,
            import_file,
            revision_number=1,
            snapshot=snapshot,
            changed_fields={"__created__": True},
        )
        bp.latest_revision_id = rev.id
        bp.first_seen_file_id = import_file.id
        bp.last_seen_file_id = import_file.id
        session.flush()

        summary["new_build_plans"] = summary.get("new_build_plans", 0) + 1
        summary["revisions_created"] = summary.get("revisions_created", 0) + 1
        return

    # ===================================================================
    # EXISTING build plan
    # ===================================================================
    revisions = sorted(bp.revisions, key=_chrono_key)

    # Same chrono-key already exists? -> touch.
    for r in revisions:
        if (
            r.work_year == import_file.work_year
            and r.work_week == import_file.work_week
            and r.file_revision == import_file.file_revision
        ):
            _record_touch(session, import_file, bp, matched_revision=r)
            summary["no_change_touches"] = summary.get("no_change_touches", 0) + 1
            return

    prev_rev = None
    next_rev = None
    for r in revisions:
        if _chrono_key(r) < chrono_in:
            prev_rev = r
        elif _chrono_key(r) > chrono_in and next_rev is None:
            next_rev = r

    # ---------------- CASE A: incoming is the newest ----------------
    if next_rev is None:
        assert prev_rev is not None, (
            "BuildPlan exists but has no revisions — invariant violated"
        )
        diff = diff_snapshot(prev_rev.snapshot, snapshot)

        if not diff:
            _record_touch(session, import_file, bp, matched_revision=prev_rev)
            bp.last_seen_file_id = import_file.id
            summary["no_change_touches"] = summary.get("no_change_touches", 0) + 1
            return

        if "plan" in diff and "status" in diff["plan"]:
            old_status_str, new_status_str = diff["plan"]["status"]
            if violates_monotonic_order(
                BuildPlanStatus(old_status_str), BuildPlanStatus(new_status_str)
            ):
                raise StatusRegressionError(
                    f"Config {config_number.value}: status would regress from "
                    f"{old_status_str} -> {new_status_str}"
                )

        rev = _create_revision(
            session,
            bp,
            import_file,
            revision_number=prev_rev.revision_number + 1,
            snapshot=snapshot,
            changed_fields=diff,
        )
        _apply_scalars(
            session,
            bp,
            snapshot,
            support_activity_resolver=seed_helpers.get_or_create_support_activity,
            build_desc_resolver=seed_helpers.get_or_create_build_desc,
        )
        _wipe_children(session, bp)
        _populate_children(session, bp, family_form_factor, parsed_column, seed_helpers)
        _link_build_notes(session, bp, snapshot, seed_helpers)
        bp.latest_revision_id = rev.id
        bp.last_seen_file_id = import_file.id
        session.flush()

        summary["revisions_created"] = summary.get("revisions_created", 0) + 1
        return

    # ---------------- CASE B: between two revisions ----------------
    if prev_rev is not None and next_rev is not None:
        diff_prev = diff_snapshot(prev_rev.snapshot, snapshot)
        if not diff_prev:
            _record_touch(session, import_file, bp, matched_revision=prev_rev)
            summary["no_change_touches"] = summary.get("no_change_touches", 0) + 1
            return

        diff_next = diff_snapshot(snapshot, next_rev.snapshot)
        if not diff_next:
            # Re-attribute next_rev to this earlier file.
            next_rev.import_file_id = import_file.id
            next_rev.work_year = import_file.work_year
            next_rev.work_week = import_file.work_week
            next_rev.file_revision = import_file.file_revision
            session.flush()
            summary["no_change_touches"] = summary.get("no_change_touches", 0) + 1
            return

        # Capture the target slot BEFORE the shift mutates next_rev in-place.
        target_revision_number = next_rev.revision_number
        _shift_revision_numbers(
            session, bp.id, start_at=target_revision_number, by=+1
        )
        _create_revision(
            session,
            bp,
            import_file,
            revision_number=target_revision_number,
            snapshot=snapshot,
            changed_fields=diff_prev,
        )
        # Canonical row + children NOT touched in CASE B.
        summary["revisions_created"] = summary.get("revisions_created", 0) + 1
        summary["revisions_inserted_midstream"] = (
            summary.get("revisions_inserted_midstream", 0) + 1
        )
        return

    # ---------------- CASE C: older than every revision ----------------
    # prev_rev is None and next_rev is not None
    diff_next = diff_snapshot(snapshot, next_rev.snapshot)
    if not diff_next:
        next_rev.import_file_id = import_file.id
        next_rev.work_year = import_file.work_year
        next_rev.work_week = import_file.work_week
        next_rev.file_revision = import_file.file_revision
        bp.first_seen_file_id = import_file.id
        session.flush()
        summary["no_change_touches"] = summary.get("no_change_touches", 0) + 1
        return

    _shift_revision_numbers(session, bp.id, start_at=1, by=+1)
    _create_revision(
        session,
        bp,
        import_file,
        revision_number=1,
        snapshot=snapshot,
        changed_fields={"__created__": True},
    )
    bp.first_seen_file_id = import_file.id
    summary["revisions_created"] = summary.get("revisions_created", 0) + 1
    summary["revisions_inserted_midstream"] = (
        summary.get("revisions_inserted_midstream", 0) + 1
    )


# ---------------------------------------------------------------------------
# Children + build notes
# ---------------------------------------------------------------------------

def _populate_children(
    session: Session,
    build_plan: BuildPlan,
    family_form_factor: FamilyFormFactor,
    parsed_column: dict,
    seed_helpers,
) -> None:
    """Re-create children from parsed Excel column. Caller should have wiped
    pre-existing children first if updating an existing plan."""
    seed_helpers.import_key_components(
        session=session,
        build_plan=build_plan,
        key_components=parsed_column.get("key_components") or {},
        family_form_factor=family_form_factor,
    )
    seed_helpers.import_silicon_steppings(
        session=session,
        build_plan=build_plan,
        key_components=parsed_column.get("key_components") or {},
    )
    seed_helpers.import_test_section(
        session=session,
        build_plan=build_plan,
        test_section=parsed_column.get("test_section") or {},
    )
    samples = parsed_column.get("samples") or []
    seed_helpers.import_build_requests(
        session=session,
        build_plan=build_plan,
        family_form_factor=family_form_factor,
        samples=samples,
    )
    seed_helpers.import_build_plan_shippings(
        session=session,
        build_plan=build_plan,
        samples=samples,
    )
    seed_helpers.import_warehouse_quantities(
        session=session,
        build_plan=build_plan,
        warehouse_quantities=parsed_column.get("warehouse_quantities") or {},
    )


def _link_build_notes(
    session: Session,
    build_plan: BuildPlan,
    snapshot: dict,
    seed_helpers,
) -> None:
    """Link snapshot.plan.build_notes to the build plan + support activity."""
    from app.models.build.build_plan import (
        BuildNote,
        BuildPlanBuildNote,
    )

    notes = snapshot["plan"].get("build_notes") or []
    # Wipe existing links to keep parity with snapshot semantics.
    session.query(BuildPlanBuildNote).filter_by(
        build_plan_id=build_plan.id
    ).delete(synchronize_session=False)
    session.flush()

    if not notes:
        notes = ["N/A"]

    support_activity = build_plan.support_activity
    for note_text in notes:
        bn = seed_helpers.get_or_create(session, BuildNote, notes=note_text)
        seed_helpers.link_build_note_to_build_plan(session, build_plan, bn)
        if support_activity is not None:
            seed_helpers.link_build_note_to_support_activity(
                session, support_activity, bn
            )


# ---------------------------------------------------------------------------
# Manual revision (created from the UI, not from an Excel import)
# ---------------------------------------------------------------------------

# Status values from which a user is allowed to author a manual revision.
# Per product spec: anything except the terminal "Cancelled" status is
# mutable.
MANUAL_REVISION_ALLOWED_STATUSES = {
    BuildPlanStatus.new,
    BuildPlanStatus.plan,
    BuildPlanStatus.hold,
    BuildPlanStatus.done,
}


class ManualRevisionNotAllowedError(ValueError):
    """Raised when a manual revision is attempted on a locked build plan."""


class ManualRevisionNoChangeError(ValueError):
    """Raised when the manual payload is identical to the current snapshot."""


# Plan-scalar fields that the UI is allowed to overwrite.  Child sections
# (components / tests / build_requests / warehouse_quantities) are still
# managed via re-import in v1 and intentionally cannot be edited here.
_MANUAL_EDITABLE_PLAN_FIELDS = (
    "status",
    "support_activity",
    "build_description",
    "product_code",
    "mm_number",
    "ta_number",
    "pba_number",
    "as_number",
    "special_instruction",
    "required_quantity",
    "estimated_yield",
    "build_start_quantity",
    "build_notes",
)


def _coerce_plan_field(field: str, value: Any) -> Any:
    """Normalise a single inbound plan field to snapshot conventions."""
    if value is None:
        return None
    if field == "status":
        return _normalise_status(value)
    if field == "build_notes":
        if isinstance(value, str):
            value = [value]
        return sorted({_clean(v) for v in value if _clean(v)})
    if field == "estimated_yield":
        return _safe_percent_int(value)
    if field in ("required_quantity", "build_start_quantity"):
        if isinstance(value, (int, float)):
            return int(value)
        return _safe_int(value)
    return _clean(value)


def create_manual_revision(
    session: Session,
    *,
    build_plan: BuildPlan,
    plan_updates: dict[str, Any],
    seed_helpers,
) -> BuildPlanRevision:
    """Author a new revision driven by user-supplied field updates.

    The new snapshot is the current latest snapshot with ``plan_updates``
    merged on top of its ``plan`` section. Child sections are carried over
    unchanged. Raises :class:`ManualRevisionNotAllowedError` when the build
    plan's current status is locked and :class:`ManualRevisionNoChangeError`
    when the payload produces no effective change.
    """
    if build_plan.status not in MANUAL_REVISION_ALLOWED_STATUSES:
        raise ManualRevisionNotAllowedError(
            f"Build plan status '{build_plan.status.value}' is locked for "
            f"manual edits. Allowed: "
            f"{', '.join(s.value for s in MANUAL_REVISION_ALLOWED_STATUSES)}."
        )

    revisions = sorted(build_plan.revisions, key=_chrono_key)
    if not revisions:
        raise ManualRevisionNotAllowedError(
            "Build plan has no prior revisions; cannot author a manual edit."
        )
    latest = revisions[-1]
    base_snapshot = latest.snapshot or {}

    new_plan = dict(base_snapshot.get("plan") or {})
    for field, raw in plan_updates.items():
        if field not in _MANUAL_EDITABLE_PLAN_FIELDS:
            continue
        new_plan[field] = _coerce_plan_field(field, raw)

    new_snapshot = {
        "plan": new_plan,
        "components": list(base_snapshot.get("components") or []),
        "tests": list(base_snapshot.get("tests") or []),
        "build_requests": list(base_snapshot.get("build_requests") or []),
        "warehouse_quantities": list(base_snapshot.get("warehouse_quantities") or []),
    }

    diff = diff_snapshot(base_snapshot, new_snapshot)
    if not diff:
        raise ManualRevisionNoChangeError(
            "Submitted values match the latest revision; no new revision created."
        )

    if "plan" in diff and "status" in diff["plan"]:
        old_status_str, new_status_str = diff["plan"]["status"]
        if violates_monotonic_order(
            BuildPlanStatus(old_status_str), BuildPlanStatus(new_status_str)
        ):
            raise StatusRegressionError(
                f"Status would regress from {old_status_str} -> {new_status_str}"
            )

    rev = _create_revision(
        session,
        build_plan,
        import_file=None,
        revision_number=latest.revision_number + 1,
        snapshot=new_snapshot,
        changed_fields=diff,
    )
    _apply_scalars(
        session,
        build_plan,
        new_snapshot,
        support_activity_resolver=seed_helpers.get_or_create_support_activity,
        build_desc_resolver=seed_helpers.get_or_create_build_desc,
    )
    _link_build_notes(session, build_plan, new_snapshot, seed_helpers)
    build_plan.latest_revision_id = rev.id
    session.flush()
    return rev
