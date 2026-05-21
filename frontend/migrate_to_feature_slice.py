#!/usr/bin/env python3
"""Migrate frontend src/ to feature-slice layout.

Strategy:
  1. Define MOVES (old src-relative path -> new src-relative path).
  2. For every .js/.jsx in src, rewrite its imports:
       - Relative imports get resolved to the old absolute src path,
         remapped via MOVES, and emitted as `@/<new path>` (with extension stripped
         for .js/.jsx, kept for .css).
       - Bare imports (react, antd, zustand, ...) are left alone.
  3. Write content at new location. Remove old file.
  4. Caller is responsible for cleaning empty directories.

Run:
  python migrate_to_feature_slice.py
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# old (src-relative POSIX) -> new (src-relative POSIX)
MOVES: dict[str, str] = {
    # auth
    "pages/Login.jsx": "features/auth/pages/Login.jsx",
    "services/auth_service.js": "features/auth/services/auth_service.js",

    # buildplans
    "pages/buildplans/BuildPlanManager.jsx": "features/buildplans/pages/BuildPlanManager.jsx",
    "pages/buildplans/BuildPlanTracker.jsx": "features/buildplans/pages/BuildPlanTracker.jsx",
    "pages/buildplans/BuildplanView.jsx": "features/buildplans/pages/BuildplanView.jsx",
    "pages/admin/BuildPlanImport.jsx": "features/buildplans/pages/BuildPlanImport.jsx",
    "components/datatable/BuildPlanTable.jsx": "features/buildplans/components/BuildPlanTable.jsx",
    "components/datatable/BuildPlanTable.css": "features/buildplans/components/BuildPlanTable.css",
    "hooks/useBuildPlanTable.js": "features/buildplans/hooks/useBuildPlanTable.js",
    "services/build_plan_service.js": "features/buildplans/services/build_plan_service.js",
    "services/build_plan_revision_service.js": "features/buildplans/services/build_plan_revision_service.js",
    "services/build_plan_import_service.js": "features/buildplans/services/build_plan_import_service.js",
    "store/useBuildPlanImportStore.js": "features/buildplans/store/useBuildPlanImportStore.js",

    # orders
    "pages/build_requests/BuildRequestManager.jsx": "features/orders/pages/BuildRequestManager.jsx",
    "pages/build_requests/BuildRequestTracker.jsx": "features/orders/pages/BuildRequestTracker.jsx",
    "pages/build_requests/BuildRequestView.jsx": "features/orders/pages/BuildRequestView.jsx",
    "hooks/useBuildRequestTable.js": "features/orders/hooks/useBuildRequestTable.js",
    "services/build_request_service.js": "features/orders/services/build_request_service.js",

    # shipments
    "pages/shippings/ShippingManager.jsx": "features/shipments/pages/ShippingManager.jsx",
    "pages/shippings/ShippingTracker.jsx": "features/shipments/pages/ShippingTracker.jsx",
    "pages/shippings/ShippingView.jsx": "features/shipments/pages/ShippingView.jsx",
    "hooks/useShippingTable.js": "features/shipments/hooks/useShippingTable.js",
    "services/shipping_service.js": "features/shipments/services/shipping_service.js",

    # stocks
    "pages/stocks/DatesPage.jsx": "features/stocks/pages/DatesPage.jsx",
    "pages/stocks/FinancialFactsPage.jsx": "features/stocks/pages/FinancialFactsPage.jsx",
    "pages/stocks/MetricsPage.jsx": "features/stocks/pages/MetricsPage.jsx",
    "pages/stocks/StatementsPage.jsx": "features/stocks/pages/StatementsPage.jsx",
    "pages/stocks/StockExplorerPage.jsx": "features/stocks/pages/StockExplorerPage.jsx",
    "pages/stocks/StockMasterPage.jsx": "features/stocks/pages/StockMasterPage.jsx",
    "components/modal/DimensionImportModal.jsx": "features/stocks/components/DimensionImportModal.jsx",
    "components/modal/FactImportModal.jsx": "features/stocks/components/FactImportModal.jsx",
    "services/stock_service.js": "features/stocks/services/stock_service.js",
    "utils/stockExplorerExport.js": "features/stocks/utils/stockExplorerExport.js",
    "utils/stockExplorerTransform.js": "features/stocks/utils/stockExplorerTransform.js",

    # admin
    "pages/admin/DBTablesManagement.jsx": "features/admin/pages/DBTablesManagement.jsx",
    "pages/admin/RoleManagement.jsx": "features/admin/pages/RoleManagement.jsx",
    "pages/admin/UserManagement.jsx": "features/admin/pages/UserManagement.jsx",
    "services/role_service.js": "features/admin/services/role_service.js",
    "services/user_service.js": "features/admin/services/user_service.js",
    "services/lookup_service.js": "features/admin/services/lookup_service.js",
    "services/department_service.js": "features/admin/services/department_service.js",

    # dashboards
    "pages/dashboards/PM_Dashboard.jsx": "features/dashboards/pages/PM_Dashboard.jsx",
    "pages/dashboards/Requestor_Dashboard.jsx": "features/dashboards/pages/Requestor_Dashboard.jsx",

    # shared
    "components/datatable/PaginatedDataTable.jsx": "shared/components/PaginatedDataTable.jsx",
    "components/action/ImportExport.jsx": "shared/components/ImportExport.jsx",
    "components/action/Sidebar.jsx": "shared/components/Sidebar.jsx",
    "components/dropdown/ExportDropdown.jsx": "shared/components/ExportDropdown.jsx",
    "components/dropdown/TableExportDropdown.jsx": "shared/components/TableExportDropdown.jsx",
    "hooks/usePaginatedTable.js": "shared/hooks/usePaginatedTable.js",
    "hooks/useServerTable.js": "shared/hooks/useServerTable.js",
    "hooks/useTableExport.js": "shared/hooks/useTableExport.js",
    "layouts/MainLayout.jsx": "shared/layouts/MainLayout.jsx",
    "routes/ProtectedRoute.jsx": "shared/routes/ProtectedRoute.jsx",
    "services/helper.js": "shared/services/helper.js",
    "store/useAuthStore.js": "shared/store/useAuthStore.js",
    "utils/createStandardTableExporters.js": "shared/utils/createStandardTableExporters.js",
    "utils/exportHelpers.js": "shared/utils/exportHelpers.js",
    "utils/fetchAllPaginatedRows.js": "shared/utils/fetchAllPaginatedRows.js",
    "utils/tableDataExport.js": "shared/utils/tableDataExport.js",
    "utils/tablePdfExport.js": "shared/utils/tablePdfExport.js",
}

# Files NOT moved (stay at root): App.jsx, App.css, main.jsx, index.css, config.js, assets/*

JS_EXTS = {".js", ".jsx"}
ALL_EXTS = JS_EXTS | {".css"}

# Match: import ... from "<spec>";  OR  import "<spec>";  (also handles single quotes)
IMPORT_RE = re.compile(
    r'''(?P<prefix>(?:^|\n)\s*(?:import\s+(?:[^'"]+?\s+from\s+)?|export\s+\*\s+from\s+|export\s+\{[^}]*\}\s+from\s+))(?P<q>["'])(?P<spec>[^"']+)(?P=q)'''
)


def is_relative(spec: str) -> bool:
    return spec.startswith("./") or spec.startswith("../") or spec == "." or spec == ".."


def resolve_with_extension(target_no_ext: Path) -> str | None:
    """Given an absolute path *without* extension, find the actual file by trying
    extensions or `index.{ext}`. Return the src-relative POSIX path of that file."""
    candidates = [
        target_no_ext.with_suffix(".jsx"),
        target_no_ext.with_suffix(".js"),
        target_no_ext.with_suffix(".css"),
        target_no_ext / "index.jsx",
        target_no_ext / "index.js",
    ]
    for c in candidates:
        if c.exists():
            try:
                return c.relative_to(SRC).as_posix()
            except ValueError:
                return None
    return None


def resolve_relative_import(importer_old_relpath: str, spec: str) -> str | None:
    """Resolve a relative import spec (as written by the importer) to a src-relative POSIX path.
    Returns None if the target cannot be resolved (e.g. points outside src or doesn't exist).
    """
    importer_dir = (SRC / importer_old_relpath).parent
    target = (importer_dir / spec).resolve()

    # First, see if spec already has an extension we know.
    if target.suffix in ALL_EXTS and target.exists():
        try:
            return target.relative_to(SRC).as_posix()
        except ValueError:
            return None

    # Otherwise, try to resolve by trying extensions / index files.
    return resolve_with_extension(target)


def remap(old_relpath: str) -> str:
    """Map an old src-relative path through MOVES (or return unchanged)."""
    return MOVES.get(old_relpath, old_relpath)


def to_alias(new_relpath: str) -> str:
    """Convert a src-relative path to its `@/...` alias form. Strip .js/.jsx extension."""
    p = Path(new_relpath)
    if p.suffix in JS_EXTS:
        p = p.with_suffix("")
    return "@/" + p.as_posix()


def rewrite_file(old_relpath: str, content: str) -> str:
    def _sub(m: re.Match) -> str:
        prefix = m.group("prefix")
        q = m.group("q")
        spec = m.group("spec")
        if not is_relative(spec):
            return m.group(0)
        target_old = resolve_relative_import(old_relpath, spec)
        if target_old is None:
            print(f"  WARN: could not resolve {spec!r} from {old_relpath}", file=sys.stderr)
            return m.group(0)
        target_new = remap(target_old)
        new_spec = to_alias(target_new)
        return f"{prefix}{q}{new_spec}{q}"

    return IMPORT_RE.sub(_sub, content)


def main() -> int:
    if not SRC.is_dir():
        print(f"src/ not found at {SRC}", file=sys.stderr)
        return 1

    # Read every js/jsx/css file's content first (so we don't fight a moving filesystem).
    files: list[tuple[str, str]] = []  # (old_relpath, content)
    for path in sorted(SRC.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in ALL_EXTS:
            continue
        rel = path.relative_to(SRC).as_posix()
        files.append((rel, path.read_text(encoding="utf-8")))

    print(f"Processing {len(files)} files...")

    # Phase 1: rewrite imports for every js/jsx file. CSS files don't need rewrites.
    for old_rel, content in files:
        new_rel = remap(old_rel)
        new_path = SRC / new_rel
        new_path.parent.mkdir(parents=True, exist_ok=True)

        if Path(old_rel).suffix in JS_EXTS:
            new_content = rewrite_file(old_rel, content)
        else:
            new_content = content

        new_path.write_text(new_content, encoding="utf-8")
        if old_rel != new_rel:
            print(f"  MOVED {old_rel} -> {new_rel}")

    # Phase 2: delete originals that were moved.
    for old_rel in MOVES:
        old_path = SRC / old_rel
        new_path = SRC / MOVES[old_rel]
        if old_path.exists() and old_path.resolve() != new_path.resolve():
            old_path.unlink()

    # Phase 3: prune now-empty directories.
    for path in sorted(SRC.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass

    print("Migration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
