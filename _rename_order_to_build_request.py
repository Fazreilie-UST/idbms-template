"""One-shot rename script: Order Request -> Build Request.

- Applies case-aware string substitutions across backend, frontend, db/queries,
  and root-level docs.
- Skips alembic migrations (preserved as historical), __pycache__, node_modules,
  .git, data/, .venv, dist/, build/.
- Then renames files whose names contain the old token.

Run from repo root: `python _rename_order_to_build_request.py`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

# (old, new) — order matters: PascalCase before snake before space variants
# so substitutions don't cascade incorrectly.
REPLACEMENTS = [
    ("OrderRequest", "BuildRequest"),
    ("orderrequest", "buildrequest"),
    ("order_request", "build_request"),
    ("order-request", "build-request"),
    ("Order Request", "Build Request"),
    ("Order request", "Build request"),
    ("order request", "build request"),
]

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "dist",
    ".next",
    "data",
    "build plan",
    "build-plans",
    "shippings",
    "stock",
    "original_data",
    "transformed_data",
    "etl_scripts",
}
EXCLUDE_PATH_SUFFIXES = (
    os.path.normpath("backend/alembic/versions"),
)

TEXT_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".sql",
    ".md", ".css", ".html", ".sh", ".yml", ".yaml", ".txt",
    ".ini", ".cfg", ".toml", ".env",
}

FILE_RENAMES = [
    # backend models
    ("backend/app/models/order/order_request.py",
     "backend/app/models/order/build_request.py"),
    ("backend/app/models/order/user_order_request.py",
     "backend/app/models/order/user_build_request.py"),
    ("backend/app/models/build/build_plan_order_request.py",
     "backend/app/models/build/build_plan_build_request.py"),
    # backend schemas
    ("backend/app/schemas/order/order_request.py",
     "backend/app/schemas/order/build_request.py"),
    # backend service
    ("backend/app/services/order_request_service.py",
     "backend/app/services/build_request_service.py"),
    # backend endpoint
    ("backend/app/api/v1/endpoints/order_requests.py",
     "backend/app/api/v1/endpoints/build_requests.py"),
    # frontend pages
    ("frontend/src/features/orders/pages/OrderRequestManager.jsx",
     "frontend/src/features/orders/pages/BuildRequestManager.jsx"),
    ("frontend/src/features/orders/pages/OrderRequestTracker.jsx",
     "frontend/src/features/orders/pages/BuildRequestTracker.jsx"),
    ("frontend/src/features/orders/pages/OrderRequestView.jsx",
     "frontend/src/features/orders/pages/BuildRequestView.jsx"),
    # frontend hook
    ("frontend/src/features/orders/hooks/useOrderRequestTable.js",
     "frontend/src/features/orders/hooks/useBuildRequestTable.js"),
    # frontend service
    ("frontend/src/features/orders/services/order_request_service.js",
     "frontend/src/features/orders/services/build_request_service.js"),
    # SQL query
    ("db/queries/order_request.sql",
     "db/queries/build_request.sql"),
]


def should_skip_dir(p: Path) -> bool:
    if p.name in EXCLUDE_DIR_NAMES:
        return True
    rel = str(p.relative_to(REPO)).replace("\\", "/")
    if rel.startswith("backend/alembic/versions"):
        return True
    return False


def transform(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def sweep() -> list[Path]:
    changed: list[Path] = []
    for root, dirs, files in os.walk(REPO):
        root_p = Path(root)
        dirs[:] = [d for d in dirs if not should_skip_dir(root_p / d)]
        for fname in files:
            p = root_p / fname
            if p.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                rel = p.relative_to(REPO)
            except ValueError:
                continue
            rel_str = str(rel).replace("\\", "/")
            if rel_str.startswith("backend/alembic/versions/"):
                continue
            # Skip this script itself
            if p.name == Path(__file__).name:
                continue
            try:
                original = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            new_text = transform(original)
            if new_text != original:
                p.write_text(new_text, encoding="utf-8", newline="\n" if "\r\n" not in original else None)
                # preserve original line endings if possible
                if "\r\n" in original and "\r\n" not in new_text:
                    p.write_bytes(new_text.replace("\n", "\r\n").encode("utf-8"))
                changed.append(p)
    return changed


def rename_files() -> list[tuple[str, str]]:
    done: list[tuple[str, str]] = []
    for old, new in FILE_RENAMES:
        src = REPO / old
        dst = REPO / new
        if not src.exists():
            print(f"  SKIP (missing): {old}")
            continue
        if dst.exists():
            print(f"  SKIP (target exists): {new}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        done.append((old, new))
        print(f"  RENAMED: {old} -> {new}")
    return done


def main() -> int:
    print("== Phase 1: text substitution ==")
    changed = sweep()
    print(f"  {len(changed)} files modified")
    print()
    print("== Phase 2: file renames ==")
    rename_files()
    return 0


if __name__ == "__main__":
    sys.exit(main())
