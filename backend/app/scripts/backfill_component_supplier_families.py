"""Backfill ``component_supplier_families`` from existing build plan data.

For every ``BuildPlanComponent`` row with a ``supplier_id`` we already know the
family (via ``BuildPlan.family_form_factor_id -> FamilyFormFactor.family_id``).
That triple ``(component_id, supplier_id, family_id)`` is exactly what the new
``component_supplier_families`` junction stores -- but historic build plans were
ingested before that table existed, so the assignments are missing in the UI.

This script scans every build plan component, ensures the corresponding
``component_suppliers`` row exists, and inserts the matching
``component_supplier_families`` row when it is not already present.  Re-running
is safe (idempotent).

Usage::

    python -m app.scripts.backfill_component_supplier_families
"""
from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.build.build_plan import BuildPlan
from app.models.build.build_plan_component import BuildPlanComponent
from app.models.build.component_supplier import ComponentSupplier
from app.models.build.component_supplier_family import ComponentSupplierFamily
from app.models.build.family_form_factor import FamilyFormFactor


logger = logging.getLogger(__name__)


def backfill(session: Session) -> dict:
    """Populate component_supplier_families from build_plan_components.

    Returns a stats dict with counts of inserted / skipped rows.
    """
    # family_form_factor_id -> family_id
    ff_to_family: dict[int, int] = dict(
        session.query(FamilyFormFactor.id, FamilyFormFactor.family_id).all()
    )

    # build_plan_id -> family_id (via family_form_factor)
    bp_to_family: dict[int, int] = {}
    for bp_id, ff_id in session.query(
        BuildPlan.id, BuildPlan.family_form_factor_id
    ).all():
        if ff_id is None:
            continue
        fam_id = ff_to_family.get(ff_id)
        if fam_id is not None:
            bp_to_family[bp_id] = fam_id

    # Existing (component_id, supplier_id) pairs in component_suppliers.
    existing_cs: set[tuple[int, int]] = set(
        session.query(
            ComponentSupplier.component_id, ComponentSupplier.supplier_id
        ).all()
    )

    # Existing (component_id, supplier_id, family_id) triples in CSF.
    existing_csf: set[tuple[int, int, int]] = set(
        session.query(
            ComponentSupplierFamily.component_id,
            ComponentSupplierFamily.supplier_id,
            ComponentSupplierFamily.family_id,
        ).all()
    )

    # Collect unique triples from build plan components.
    triples: set[tuple[int, int, int]] = set()
    skipped_no_family = 0
    skipped_no_supplier = 0
    rows = session.query(
        BuildPlanComponent.build_plan_id,
        BuildPlanComponent.component_id,
        BuildPlanComponent.supplier_id,
    ).all()
    for bp_id, comp_id, sup_id in rows:
        if sup_id is None or comp_id is None:
            skipped_no_supplier += 1
            continue
        fam_id = bp_to_family.get(bp_id)
        if fam_id is None:
            skipped_no_family += 1
            continue
        triples.add((comp_id, sup_id, fam_id))

    # Ensure component_suppliers rows exist (CSF has a composite FK to it).
    cs_inserted = 0
    for comp_id, sup_id, _fam_id in triples:
        if (comp_id, sup_id) not in existing_cs:
            session.add(
                ComponentSupplier(component_id=comp_id, supplier_id=sup_id)
            )
            existing_cs.add((comp_id, sup_id))
            cs_inserted += 1

    # Flush so the new component_suppliers rows are visible to the CSF inserts.
    if cs_inserted:
        session.flush()

    # Insert CSF rows that are not already present.
    csf_inserted = 0
    per_family: dict[int, int] = defaultdict(int)
    for comp_id, sup_id, fam_id in triples:
        if (comp_id, sup_id, fam_id) in existing_csf:
            continue
        session.add(
            ComponentSupplierFamily(
                component_id=comp_id,
                supplier_id=sup_id,
                family_id=fam_id,
            )
        )
        existing_csf.add((comp_id, sup_id, fam_id))
        csf_inserted += 1
        per_family[fam_id] += 1

    return {
        "build_plan_components_scanned": len(rows),
        "unique_triples": len(triples),
        "component_suppliers_inserted": cs_inserted,
        "component_supplier_families_inserted": csf_inserted,
        "skipped_no_supplier": skipped_no_supplier,
        "skipped_no_family": skipped_no_family,
        "inserted_per_family": dict(per_family),
    }


def main() -> dict:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    session = SessionLocal()
    try:
        stats = backfill(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(
        "Scanned {build_plan_components_scanned} build_plan_components row(s); "
        "derived {unique_triples} unique (component, supplier, family) triple(s).".format(
            **stats
        )
    )
    print(
        "  inserted {component_suppliers_inserted} component_suppliers row(s)".format(
            **stats
        )
    )
    print(
        "  inserted {component_supplier_families_inserted} component_supplier_families row(s)".format(
            **stats
        )
    )
    if stats["skipped_no_supplier"]:
        print(
            f"  skipped {stats['skipped_no_supplier']} row(s) with no supplier_id"
        )
    if stats["skipped_no_family"]:
        print(
            f"  skipped {stats['skipped_no_family']} row(s) whose build plan has no resolvable family"
        )
    if stats["inserted_per_family"]:
        print("  inserted CSF rows per family_id:")
        for fam_id, n in sorted(stats["inserted_per_family"].items()):
            print(f"    family_id={fam_id}: {n}")
    return stats


if __name__ == "__main__":
    main()
