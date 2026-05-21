#!/usr/bin/env python3
"""Phase-2 cleanup sweep for the SKU -> Form Factor rename.

Handles the remaining structural occurrences that the first sweep
(_rename_sweep.py) could not handle mechanically:

* Raw SQL fragments (``LEFT JOIN skus s`` -> ``LEFT JOIN form_factors s``,
  ``s.name AS sku_code`` -> ``s.name AS form_factor``).
* Service / repository / API dict keys (``"sku_code"`` -> ``"form_factor"``).
* Filter / sort identifiers (``sku_code_values`` -> ``form_factor_values``,
  ``BuildPlanSortBy.sku_code`` -> ``BuildPlanSortBy.form_factor``,
  ``query.sku_code`` -> ``query.form_factor``).
* Frontend stragglers (``family.skus``, ``data?.skus``, ``colorField:
  "sku_name"``, etc.).

Run from the repo root:

    python3 backend/_rename_sweep2.py

It is idempotent: running it twice is a no-op on the second run.
"""
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Backend rules (Python)
# ---------------------------------------------------------------------------

BACKEND_FILES = [
    "backend/app/services/build_plan_service.py",
    "backend/app/services/build_plan_revision_service.py",
    "backend/app/api/v1/endpoints/build_plans.py",
    "backend/app/api/v1/endpoints/dashboard.py",
]

BACKEND_RULES: list[tuple[str, str]] = [
    # SQL JOIN aliases / projections
    (r"\bJOIN skus s\b", "JOIN form_factors s"),
    (r"\bFROM skus s\b", "FROM form_factors s"),
    (r"s\.name AS sku_code", "s.name AS form_factor"),
    (r"s\.name AS sku_name", "s.name AS form_factor"),
    # Group-by / order-by referring to sku_code/sku_name aliases
    (r"\bsku_code\b(?=\s*[,)\n])", "form_factor"),

    # Identifier renames in Python code
    (r"BuildPlanSortBy\.sku_code", "BuildPlanSortBy.form_factor"),
    (r"\.sku_code(?=\s*[,)\]\.\s=:])", ".form_factor"),
    (r"\.sku_code$", ".form_factor"),
    (r"query\.sku_code", "query.form_factor"),
    (r"row\[\"sku_code\"\]", 'row["form_factor"]'),
    (r"target\[\"sku_code\"\]", 'target["form_factor"]'),

    # Dict keys
    (r'"sku_code"', '"form_factor"'),
    (r'"sku_code_values"', '"form_factor_values"'),
    (r"'sku_code'", "'form_factor'"),

    # Endpoint query-param kwargs (sku_codes=sku_code on dashboard)
    (r"\bsku_codes=sku_code\b", "form_factors=form_factor"),
    (r"\bsku_code:\s*List\[str\]", "form_factor: List[str]"),
    (r"\bsku_code:\s*str\s*\|\s*None", "form_factor: str | None"),
    (r"\bsku_code:\s*Optional\[str\]", "form_factor: Optional[str]"),
    (r"info\.get\(\"sku_code\"\)", 'info.get("form_factor")'),

    # Local variable / kwarg names
    (r"\bsku_code(?=\s*=\s*)", "form_factor"),
    (r"\bsku_code(?=\s*,)", "form_factor"),
    (r"\bsku_code(?=\s*\))", "form_factor"),

    # Plurals (drops from filter dropdown)
    (r"\bsku_codes\b", "form_factors"),
    (r"\bsku_names\b", "form_factors"),
]


# ---------------------------------------------------------------------------
# Frontend rules (JS / JSX)
# ---------------------------------------------------------------------------

FRONTEND_FILES = [
    "frontend/src/features/dashboards/components/RequiredQuantityTopBar.jsx",
    "frontend/src/features/dashboards/components/FamilyDonutGrid.jsx",
    "frontend/src/features/dashboards/components/FamilyComparisonPanel.jsx",
    "frontend/src/features/buildplans/hooks/useBuildPlanTable.js",
    "frontend/src/features/buildplans/components/BuildPlanTable.jsx",
    "frontend/src/features/buildplans/services/build_plan_service.js",
]

FRONTEND_RULES: list[tuple[str, str]] = [
    (r"\bsku_name\b", "form_factor"),
    (r"\bsku_code\b", "form_factor"),
    (r"family\.skus\b", "family.form_factors"),
    (r"data\?\.skus\b", "data?.form_factors"),
    (r"filterOptions\?\.sku_code\b", "filterOptions?.form_factor"),
    (r"filters\?\.sku_code\b", "filters?.form_factor"),
    (r"\bskus\.map\b", "form_factors.map"),
    (r"\bskus\.length\b", "form_factors.length"),
    (r"const skus\b", "const formFactors"),
    (r"let skus\b", "let formFactors"),
    (r"\{ skus \}", "{ form_factors: formFactors }"),
    # User-facing labels
    (r"\bSKUs\b", "Form Factors"),
    (r"\bSKU\b", "Form Factor"),
]


def apply_rules(text: str, rules: list[tuple[str, str]]) -> tuple[str, int]:
    changes = 0
    for pat, repl in rules:
        new_text, n = re.subn(pat, repl, text)
        if n:
            changes += n
            text = new_text
    return text, changes


def main() -> int:
    total_files = 0
    total_changes = 0

    for rel in BACKEND_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated, n = apply_rules(original, BACKEND_RULES)
        if n:
            path.write_text(updated, encoding="utf-8")
            print(f"  backend {rel}: {n} replacements")
            total_files += 1
            total_changes += n

    for rel in FRONTEND_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated, n = apply_rules(original, FRONTEND_RULES)
        if n:
            path.write_text(updated, encoding="utf-8")
            print(f"  frontend {rel}: {n} replacements")
            total_files += 1
            total_changes += n

    print(f"\nDone. {total_changes} replacements across {total_files} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
