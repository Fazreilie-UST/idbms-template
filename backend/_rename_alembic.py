#!/usr/bin/env python3
"""One-shot rename + column-drop applied to the initial alembic migrations.

Run from the repo root via:
    python backend/_rename_alembic.py

Idempotent: re-running is a no-op once renames are applied.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
VERSIONS = REPO / "alembic" / "versions"
INITIAL = VERSIONS / "151b7c009145_initial_schema.py"
RENAME = VERSIONS / "a1b2c3d4e5f6_rename_order_request_to_build_request.py"

# Token replacements applied to both files.
TOKEN_REPLACEMENTS = [
    ("family_sku_id", "family_form_factor_id"),
    ("family_skus", "family_form_factors"),
    ("ix_skus_", "ix_form_factors_"),
    ("'skus'", "'form_factors'"),
    ("skus.id", "form_factors.id"),
    (
        "uq_build_plan_access_family_sku_user",
        "uq_build_plan_access_family_form_factor_user",
    ),
    (
        "uq_build_plan_family_sku_config_number",
        "uq_build_plan_family_form_factor_config_number",
    ),
    ("ix_family_skus_id", "ix_family_form_factors_id"),
    ("ix_build_plans_family_sku_id", "ix_build_plans_family_form_factor_id"),
    ("ix_order_requests_family_sku_id", "ix_order_requests_family_form_factor_id"),
    ("ix_build_requests_family_sku_id", "ix_build_requests_family_form_factor_id"),
]


def apply_token_subs(path: Path) -> None:
    text = path.read_text()
    for old, new in TOKEN_REPLACEMENTS:
        text = text.replace(old, new)
    path.write_text(text)


def drop_code_and_form_factor_columns(path: Path) -> None:
    """Drop the now-redundant `code` and `form_factor` columns from the
    form_factors table block in the initial migration."""
    text = path.read_text()
    patterns = [
        # code column
        r"^[ \t]*sa\.Column\('code', sa\.String\(\), nullable=False\),\n",
        # form_factor enum column (single line, regardless of nested quotes)
        r"^[ \t]*sa\.Column\('form_factor', sa\.Enum\([^\n]*\),\n",
        # upgrade-side index on code
        r"^[ \t]*op\.create_index\(op\.f\('ix_form_factors_code'\)[^\n]*\n",
        # downgrade-side index on code
        r"^[ \t]*op\.drop_index\(op\.f\('ix_form_factors_code'\)[^\n]*\n",
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.MULTILINE)
    path.write_text(text)


def add_suffix_to_silicon_stepping_link(path: Path) -> None:
    text = path.read_text()
    old_col_line = (
        "    sa.Column('silicon_stepping_id', sa.Integer(), nullable=False),\n"
    )
    new_col_block = (
        old_col_line
        + "    sa.Column('suffix', sa.String(), nullable=True),\n"
    )
    if "sa.Column('suffix', sa.String(), nullable=True)" not in text:
        # Only patch the silicon-stepping link table, not all occurrences.
        # The exact line above appears once in the m2m link block.
        text = text.replace(old_col_line, new_col_block, 1)

    text = text.replace(
        "sa.UniqueConstraint('build_plan_id', 'silicon_stepping_id', name='uq_build_plan_silicon_stepping')",
        "sa.UniqueConstraint('build_plan_id', 'silicon_stepping_id', 'suffix', name='uq_build_plan_silicon_stepping_suffix')",
    )
    path.write_text(text)


def main() -> None:
    for f in (INITIAL, RENAME):
        apply_token_subs(f)
    drop_code_and_form_factor_columns(INITIAL)
    add_suffix_to_silicon_stepping_link(INITIAL)
    print(f"Updated: {INITIAL}")
    print(f"Updated: {RENAME}")


if __name__ == "__main__":
    main()
