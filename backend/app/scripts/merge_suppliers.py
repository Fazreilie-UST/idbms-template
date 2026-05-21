"""Merge duplicate supplier rows into their canonical entries.

Reads ``SUPPLIER_ALIASES`` from :mod:`app.scripts.seed_build_plan` and:

1. Ensures every canonical supplier (e.g. ``"SpeedTech"``) exists.
2. Repoints every reference to an alias supplier
   (``build_plan_components.supplier_id``, ``component_suppliers``,
   ``component_supplier_families``) to the canonical row.
3. Deletes the now-orphaned alias supplier rows.

Run it after a fresh seed (or any time the spreadsheet has introduced new
spellings) to keep the suppliers table clean. Safe to re-run.

Usage::

    python -m app.scripts.merge_suppliers
"""
from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.scripts.seed_build_plan import (
    SUPPLIER_ALIASES,
    merge_duplicate_suppliers,
)


logger = logging.getLogger(__name__)


def main() -> dict:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    session = SessionLocal()
    try:
        stats = merge_duplicate_suppliers(session, SUPPLIER_ALIASES)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(
        "Merged {merged_pairs} duplicate supplier(s); deleted {deleted_suppliers} row(s).".format(
            **stats
        )
    )
    for table, n in stats["repointed"].items():
        print(f"  repointed {n:>5} row(s) in {table}")
    return stats


if __name__ == "__main__":
    main()
