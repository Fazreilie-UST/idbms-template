#!/usr/bin/env python3
"""Mass rename: SKU -> FormFactor across the codebase.

Applies a curated list of literal text substitutions across all Python files
under backend/ (excluding alembic versions, which have already been edited)
and all JS/JSX/TS/TSX files under frontend/src/.

Run from the repo root:
    python backend/_rename_sweep.py

Safe to re-run: substitutions are idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parent.parent  # repo root
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"


# -- Python: order matters! longer / more specific tokens first ----------------
PY_REPLACEMENTS: list[tuple[str, str]] = [
    # ---- imports ----
    (
        "from app.models.build.sku import SKU, SKUFormFactor",
        "from app.models.build.form_factor import FormFactor",
    ),
    (
        "from app.models.build.sku import SKU",
        "from app.models.build.form_factor import FormFactor",
    ),
    (
        "from app.models.build.family_sku import FamilySKU",
        "from app.models.build.family_form_factor import FamilyFormFactor",
    ),

    # ---- relationship strings / class identifiers ----
    (r'"FamilySKU"', r'"FamilyFormFactor"'),
    ("'FamilySKU'", "'FamilyFormFactor'"),
    ("FamilySKU", "FamilyFormFactor"),
    # SKUFormFactor enum no longer exists; callers must be updated manually,
    # but to surface remaining usages we replace the enum reference with a
    # name that won't import, forcing a clean compile failure rather than
    # silent behaviour change.
    ("SKUFormFactor.standard", "None  # SKUFormFactor removed"),
    ("SKUFormFactor.adaptor", "None  # SKUFormFactor removed"),
    ("SKUFormFactor.lte_adaptor", "None  # SKUFormFactor removed"),
    ("SKUFormFactor.other", "None  # SKUFormFactor removed"),
    ("SKUFormFactor", "None  # SKUFormFactor removed"),
    # Plain SKU model class
    (r'\bSKU\b', "FormFactor"),

    # ---- column / attribute names ----
    ("family_sku_id", "family_form_factor_id"),
    ("family_skus", "family_form_factors"),  # both table and attribute
    ("family_sku", "family_form_factor"),
    # NB: bare `sku_id` only appears in alembic now (already handled); keep
    # a replacement anyway in case scripts/services reference it.
    (r"\bsku_id\b", "form_factor_id"),
]

# Regex-based substitutions for Python.
PY_REGEX_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p), r) for p, r in [
        (r"\bSKU\b", "FormFactor"),
        (r"\bsku_id\b", "form_factor_id"),
    ]
]


# Bare-string substitutions that are unambiguous to apply.
PY_PLAIN_REPLACEMENTS: list[tuple[str, str]] = [
    (
        "from app.models.build.sku import SKU, SKUFormFactor",
        "from app.models.build.form_factor import FormFactor",
    ),
    (
        "from app.models.build.sku import SKU",
        "from app.models.build.form_factor import FormFactor",
    ),
    (
        "from app.models.build.family_sku import FamilySKU",
        "from app.models.build.family_form_factor import FamilyFormFactor",
    ),
    ('"FamilySKU"', '"FamilyFormFactor"'),
    ("'FamilySKU'", "'FamilyFormFactor'"),
    ("FamilySKU", "FamilyFormFactor"),
    ("SKUFormFactor.standard", "None  # SKUFormFactor removed"),
    ("SKUFormFactor.adaptor", "None  # SKUFormFactor removed"),
    ("SKUFormFactor.lte_adaptor", "None  # SKUFormFactor removed"),
    ("SKUFormFactor.other", "None  # SKUFormFactor removed"),
    ("SKUFormFactor", "None  # SKUFormFactor removed"),
    ("family_sku_id", "family_form_factor_id"),
    ("family_skus", "family_form_factors"),
    ("family_sku", "family_form_factor"),
]


def iter_python_files() -> Iterable[Path]:
    for p in BACKEND.rglob("*.py"):
        rel = p.relative_to(BACKEND)
        parts = rel.parts
        # Skip alembic versions (already edited) + caches.
        if parts and parts[0] == "alembic" and "versions" in parts:
            continue
        if "__pycache__" in parts:
            continue
        # Skip the rename script itself.
        if p.name in {"_rename_alembic.py", "_rename_sweep.py"}:
            continue
        yield p


def apply_to_python_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    # 1) Plain string substitutions.
    for old, new in PY_PLAIN_REPLACEMENTS:
        text = text.replace(old, new)
    # 2) Regex substitutions for word-bounded SKU and sku_id.
    for pat, repl in PY_REGEX_REPLACEMENTS:
        text = pat.sub(repl, text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


# -- JS / TS rename ------------------------------------------------------------
JS_PLAIN_REPLACEMENTS: list[tuple[str, str]] = [
    # API field renames (collapse sku_code+sku_name to form_factor).
    # `sku_name || sku_code` patterns become `form_factor`.
    ("r.sku_name || r.sku_code", "r.form_factor"),
    ("s.sku_name || s.sku_code", "s.form_factor"),
    ("data?.sku_code", "data?.form_factor"),
    ("r.sku_code", "r.form_factor"),
    ("s.sku_code", "s.form_factor"),
    ("s.sku_name", "s.form_factor"),
    ("r.sku_name", "r.form_factor"),
    # Filter key
    ("skuCodes", "formFactors"),
    # KPI / lookup fields
    ("data?.total_skus", "data?.total_form_factors"),
    ("lookups?.skus", "lookups?.form_factors"),
    # Local variable used by FilterBar
    ("skuOptions", "formFactorOptions"),
    ("skuInput", "formFactorInput"),
    ("setSkuInput", "setFormFactorInput"),
    # Server filter param key
    ("sku_code: filters.formFactors", "form_factor: filters.formFactors"),
    # Build plan table column / filter
    ('"sku_code"', '"form_factor"'),
    ("'sku_code'", "'form_factor'"),
    # API JSON field names (these survive after the collapse).
    ("sku_code:", "form_factor:"),
    ("sku_name:", "form_factor_name:"),
    # User-facing labels (case-sensitive).
    ("Family / SKU", "Family / Form Factor"),
    ("Search family / SKU", "Search family / form factor"),
    ('placeholder="SKU"', 'placeholder="Form Factor"'),
    ('placeholder="SKU Name"', 'placeholder="Form Factor"'),
    ('title: "SKU"', 'title: "Form Factor"'),
    ('label="SKU"', 'label="Form Factor"'),
    ("SKU: ", "Form Factor: "),
    ("SKUs", "Form Factors"),
    ('"SKUs"', '"Form Factors"'),
    # Filter UI label list
    ('["formFactors", "SKU"]', '["formFactors", "Form Factor"]'),
    # Dashboard chart title change requested by the user.
    (
        "Required Quantity by Family",
        "Required Build Quantity by Family",
    ),
]


def iter_frontend_files() -> Iterable[Path]:
    src = FRONTEND / "src"
    if not src.exists():
        return
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        for p in src.rglob(ext):
            if "node_modules" in p.parts:
                continue
            yield p


def apply_to_frontend_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    for old, new in JS_PLAIN_REPLACEMENTS:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    py_changed = 0
    for p in iter_python_files():
        if apply_to_python_file(p):
            py_changed += 1
            print(f"  py  {p.relative_to(REPO)}")
    print(f"Python files updated: {py_changed}")

    js_changed = 0
    for p in iter_frontend_files():
        if apply_to_frontend_file(p):
            js_changed += 1
            print(f"  js  {p.relative_to(REPO)}")
    print(f"Frontend files updated: {js_changed}")


if __name__ == "__main__":
    main()
