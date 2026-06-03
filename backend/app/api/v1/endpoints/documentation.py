"""Documentation API.

User-facing guides and developer references stored as Markdown files in the
repository (`docs/`). Reads are open to any authenticated user; writes are
restricted to the role configured by ``settings.DOCS_EDIT_ROLE`` (Admin by
default) so updates can be committed to version control.

All file paths are validated against an in-memory whitelist (the documentation
"tree") to prevent path traversal or arbitrary file writes.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.logging import audit_logger, security_logger
from app.models.auth.user import User


router = APIRouter(prefix="/docs", tags=["Documentation"])


<<<<<<< Updated upstream
# ---------------------------------------------------------------------------
# Documentation tree (default structure required by the product spec).
# Each leaf has a ``path`` relative to ``settings.DOCS_DIR`` and a stable
# ``key`` the frontend uses for routing. The tree is the single source of
# truth: only files referenced here can be read or written via this API.
# ---------------------------------------------------------------------------

DOC_TREE: list[dict[str, Any]] = [
    {
        "key": "user-guide",
        "label": "User Guide",
        "children": [
            {
                "key": "screen-guide",
                "label": "Screen Guide",
                "path": "user-guide/screen-guide.md",
            },
            {
                "key": "admin",
                "label": "Admin",
                "path": "user-guide/admin.md",
            },
            {
                "key": "program-manager",
                "label": "Program Manager",
                "path": "user-guide/program-manager.md",
            },
            {
                "key": "requestor",
                "label": "Requestor",
                "path": "user-guide/requestor.md",
            },
        ],
    },
    {
        "key": "developer",
        "label": "Developer",
        "children": [
            {
                "key": "api-documentation",
                "label": "API Documentation",
                "path": "developer/api-documentation.md",
                # The frontend renders an embedded Swagger UI alongside the
                # markdown body for this page.
                "embed": "swagger",
            },
            {
                "key": "db-erd",
                "label": "DB ERD",
                "children": [
                    {
                        "key": "current-db",
                        "label": "Current Database",
                        "path": "developer/db-erd/current-db.md",
                    },
                    {
                        "key": "external-db",
                        "label": "External Database",
                        "path": "developer/db-erd/external-db.md",
                    },
                ],
            },
            {
                "key": "architecture-summary",
                "label": "System Structure & Architecture Summary",
                "path": "developer/architecture-summary.md",
            },
        ],
    },
]
=======

# ---------------------------------------------------------------------------
# Role-based Documentation Tree Generation
# ---------------------------------------------------------------------------
def get_doc_tree_for_roles(roles: set[str]) -> list[dict[str, Any]]:
    import copy
    # --- Admin/PM View ---
    # Shared trackers paths for both Admin/PM and Requestor/Viewer
    shared_trackers = [
        {"key": "build-plan", "label": "Build Plan", "path": "getting-started/admin-pm/trackers/build-plan.html"},
        {"key": "build-request", "label": "Build Request", "path": "getting-started/admin-pm/trackers/build-request.html"},
        {"key": "shipment", "label": "Shipment", "path": "getting-started/admin-pm/trackers/shipment.html"},
    ]
    admin_pm_view = {
        "key": "admin-pm-view",
        "label": "Admin/PM View",
        "children": [
            {"key": "dashboard", "label": "Dashboard", "path": "getting-started/admin-pm/dashboard.html"},
            {"key": "my-build-plan", "label": "My Build Plan", "path": "getting-started/admin-pm/my-build-plan.html"},
            {"key": "manage-build-request", "label": "Manage Build Request", "path": "getting-started/admin-pm/manage-build-request.html"},
            {
                "key": "trackers",
                "label": "Trackers",
                "children": shared_trackers,
            },
            {
                "key": "administration",
                "label": "Administration",
                "children": [
                    {"key": "import-build-plan", "label": "Import Build Plan", "path": "getting-started/admin-pm/administration/import-build-plan.html"},
                    {"key": "import-shipments", "label": "Import Shipments", "path": "getting-started/admin-pm/administration/import-shipments.html"},
                    {"key": "user-management", "label": "User Management", "path": "getting-started/admin-pm/administration/user-management.html"},
                    {"key": "role-management", "label": "Role Management", "path": "getting-started/admin-pm/administration/role-management.html"},
                    {"key": "db-tables", "label": "DB Tables", "path": "getting-started/admin-pm/administration/db-tables.html"},
                ],
            },
            {"key": "documentation", "label": "Documentation", "path": "getting-started/admin-pm/documentation.html"},
            {
                "key": "audit-logs",
                "label": "Audit & Logs",
                "children": [
                    {"key": "audit-logs", "label": "Audit Logs", "path": "getting-started/admin-pm/audit-logs.html"},
                    {"key": "bug-reports", "label": "Bug Reports", "path": "getting-started/admin-pm/bug-reports.html"},
                ],
            },
            {"key": "report-issue", "label": "Report an Issue", "path": "getting-started/admin-pm/report-issue.html"},
        ],
    }
    # --- Requestor/Viewer View ---
    requestor_view = {
        "key": "requestor-view",
        "label": "Requestor/Viewer View",
        "children": [
            {"key": "dashboard", "label": "Dashboard", "path": "getting-started/requestor/dashboard.html"},
            {"key": "my-build-request", "label": "My Build Request", "path": "getting-started/requestor/my-build-request.html"},
            {
                "key": "trackers",
                "label": "Trackers",
                "children": shared_trackers,
            },
            {"key": "documentation", "label": "Documentation", "path": "getting-started/admin-pm/documentation.html"},
            {"key": "report-issue", "label": "Report an Issue", "path": "getting-started/admin-pm/report-issue.html"},
        ],
    }
    # --- Base tree ---
    base_tree = [
        {
            "key": "getting-started",
            "label": "Getting Started",
            "children": [
                {"key": "introduction", "label": "Introduction", "path": "getting-started/introduction.html"},
                {
                    "key": "page-navigation",
                    "label": "Page Navigation",
                    # children will be filled below
                },
            ],
        },
        {
            "key": "user-guide",
            "label": "User Guide",
            "children": [
                {"key": "admin", "label": "Admin", "path": "user-guide/admin.html"},
                {"key": "program-manager", "label": "Program Manager", "path": "user-guide/program-manager.html"},
                {"key": "requestor", "label": "Requestor", "path": "user-guide/requestor.html"},
                {
                    "key": "developer",
                    "label": "Developer",
                    "children": [
                        {"key": "api-docs", "label": "API Docs", "path": "developer/api-documentation.html", "embed": "swagger"},
                        {
                            "key": "db-erd",
                            "label": "DB ERD",
                            "children": [
                                {"key": "current-db", "label": "Current DB", "path": "developer/db-erd/current-db.html"},
                                {"key": "external-db", "label": "External DB", "path": "developer/db-erd/external-db.html"},
                            ],
                        },
                        {"key": "system-architecture", "label": "System Architecture", "path": "developer/architecture-summary.html"},
                    ],
                },
            ],
        },
        {"key": "glossary", "label": "Glossary", "path": "user-guide/glossary.html"},
    ]
    # Determine role
    roles_lower = {r.lower() for r in roles}
    is_admin = "admin" in roles_lower
    is_pm = "pm" in roles_lower or "program manager" in roles_lower
    is_requestor = "requestor" in roles_lower or "viewer" in roles_lower
    # Build the navigation children based on role
    nav_children = []
    if is_admin:
        nav_children = [admin_pm_view, requestor_view]
    elif is_pm:
        nav_children = admin_pm_view["children"]
    elif is_requestor:
        nav_children = requestor_view["children"]
    else:
        nav_children = [admin_pm_view, requestor_view]
    # Insert the navigation children into the tree
    tree = copy.deepcopy(base_tree)
    for node in tree:
        if node["key"] == "getting-started":
            for child in node["children"]:
                if child["key"] == "page-navigation":
                    child["children"] = nav_children
    return tree

def get_allowed_pages_for_roles(roles: set[str]) -> dict[str, dict[str, Any]]:
    return _collect_allowed_paths(get_doc_tree_for_roles(roles))


>>>>>>> Stashed changes


def _collect_allowed_paths(tree: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for node in tree:
        if "path" in node:
            out[node["path"]] = node
        if "children" in node:
            out.update(_collect_allowed_paths(node["children"]))
    return out


<<<<<<< Updated upstream
_ALLOWED_PAGES: dict[str, dict[str, Any]] = _collect_allowed_paths(DOC_TREE)
=======

>>>>>>> Stashed changes


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

_SAFE_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _docs_root() -> Path:
    root = Path(settings.DOCS_DIR).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _assets_root() -> Path:
    root = (_docs_root() / settings.DOCS_ASSETS_SUBDIR / "screenshots").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


<<<<<<< Updated upstream
def _resolve_page_path(rel_path: str) -> Path:
    """Resolve and validate ``rel_path`` against the whitelist.

    Returns the absolute on-disk path. Raises 404 if the path is not in the
    allowed page set, 400 for malformed paths. We re-resolve and re-check the
    parent prefix as a defense in depth against symlink shenanigans.
    """
    if rel_path not in _ALLOWED_PAGES:
        raise HTTPException(status_code=404, detail="Unknown documentation page")

    # Extra belt-and-suspenders: every segment must look like a slug. The
    # whitelist already guarantees this, but a future edit to ``DOC_TREE``
    # shouldn't be able to silently introduce ``..`` or absolute paths.
=======
def _resolve_page_path(rel_path: str, allowed_pages: dict[str, dict[str, Any]]) -> Path:
    """Resolve and validate ``rel_path`` against the whitelist for the current role."""
    if rel_path not in allowed_pages:
        raise HTTPException(status_code=404, detail="Unknown documentation page")

>>>>>>> Stashed changes
    parts = rel_path.split("/")
    for segment in parts[:-1]:
        if not _SAFE_SEGMENT_RE.match(segment):
            raise HTTPException(status_code=400, detail="Invalid path segment")
<<<<<<< Updated upstream
    if not parts[-1].endswith(".md") or not _SAFE_SEGMENT_RE.match(parts[-1][:-3]):
=======
    # Accept .md or .html files
    if not (parts[-1].endswith(".md") or parts[-1].endswith(".html")):
        raise HTTPException(status_code=400, detail="Invalid page filename")
    # Validate filename slug (strip .md or .html)
    base = parts[-1][:-3] if parts[-1].endswith(".md") else parts[-1][:-5]
    if not _SAFE_SEGMENT_RE.match(base):
>>>>>>> Stashed changes
        raise HTTPException(status_code=400, detail="Invalid page filename")

    root = _docs_root()
    target = (root / rel_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        security_logger.warning("Docs path escape attempt: %s", rel_path)
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


def _require_docs_editor(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that gates write endpoints on the configured editor role."""
    roles = getattr(current_user, "token_roles", set()) or set()
    if settings.DOCS_EDIT_ROLE not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can edit documentation",
        )
    return current_user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DocPageContent(BaseModel):
    path: str
    label: str
    content: str
    updated_at: datetime | None = None
    embed: str | None = None
    can_edit: bool = False
<<<<<<< Updated upstream
=======
    format: str = "markdown"  # "markdown" or "html"
>>>>>>> Stashed changes


class DocPageUpdate(BaseModel):
    content: str = Field(..., max_length=2 * 1024 * 1024)  # 2 MB of text


class DocAsset(BaseModel):
    filename: str
    url: str
    size_bytes: int
    uploaded_at: datetime


class DocAssetList(BaseModel):
    assets: list[DocAsset]


class DocTreeResponse(BaseModel):
    tree: list[dict[str, Any]]
    can_edit: bool
    assets_url_prefix: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tree", response_model=DocTreeResponse)
def get_doc_tree(current_user: User = Depends(get_current_user)) -> DocTreeResponse:
    roles = getattr(current_user, "token_roles", set()) or set()
    return DocTreeResponse(
<<<<<<< Updated upstream
        tree=DOC_TREE,
=======
        tree=get_doc_tree_for_roles(roles),
>>>>>>> Stashed changes
        can_edit=settings.DOCS_EDIT_ROLE in roles,
        assets_url_prefix=settings.DOCS_ASSETS_URL_PREFIX,
    )


@router.get("/page", response_model=DocPageContent)
def get_doc_page(
    path: str,
    current_user: User = Depends(get_current_user),
) -> DocPageContent:
    """Return the markdown content for ``path`` (relative to docs root)."""
<<<<<<< Updated upstream
    node = _ALLOWED_PAGES.get(path)
    if node is None:
        raise HTTPException(status_code=404, detail="Unknown documentation page")

    target = _resolve_page_path(path)
=======
    roles = getattr(current_user, "token_roles", set()) or set()
    allowed_pages = get_allowed_pages_for_roles(roles)
    node = allowed_pages.get(path)
    if node is None:
        raise HTTPException(status_code=404, detail="Unknown documentation page")

    target = _resolve_page_path(path, allowed_pages=allowed_pages)
>>>>>>> Stashed changes
    content = ""
    updated_at: datetime | None = None
    if target.exists():
        try:
            content = target.read_text(encoding="utf-8")
            updated_at = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Could not read page: {exc}")

<<<<<<< Updated upstream
    roles = getattr(current_user, "token_roles", set()) or set()
=======
    fmt = "html" if path.endswith(".html") else "markdown"
>>>>>>> Stashed changes
    return DocPageContent(
        path=path,
        label=node.get("label", path),
        content=content,
        updated_at=updated_at,
        embed=node.get("embed"),
        can_edit=settings.DOCS_EDIT_ROLE in roles,
<<<<<<< Updated upstream
=======
        format=fmt,
>>>>>>> Stashed changes
    )


@router.put("/page", response_model=DocPageContent)
def update_doc_page(
    path: str,
    payload: DocPageUpdate,
    current_user: User = Depends(_require_docs_editor),
) -> DocPageContent:
    """Replace the markdown content for ``path``. Admin-only."""
<<<<<<< Updated upstream
    node = _ALLOWED_PAGES.get(path)
    if node is None:
        raise HTTPException(status_code=404, detail="Unknown documentation page")

    target = _resolve_page_path(path)
=======
    roles = getattr(current_user, "token_roles", set()) or set()
    allowed_pages = get_allowed_pages_for_roles(roles)
    node = allowed_pages.get(path)
    if node is None:
        raise HTTPException(status_code=404, detail="Unknown documentation page")

    target = _resolve_page_path(path, allowed_pages=allowed_pages)
>>>>>>> Stashed changes
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Atomic-ish write: write to a temp file then rename so a crash mid-
        # write doesn't leave a half-written markdown page on disk.
        tmp_path = target.with_suffix(target.suffix + f".tmp-{secrets.token_hex(4)}")
        tmp_path.write_text(payload.content, encoding="utf-8")
        tmp_path.replace(target)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not write page: {exc}")

    audit_logger.info(
        "Documentation page updated: path=%s by=%s bytes=%d",
        path,
        current_user.id,
        len(payload.content.encode("utf-8")),
    )

    return DocPageContent(
        path=path,
        label=node.get("label", path),
        content=payload.content,
        updated_at=datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc),
        embed=node.get("embed"),
        can_edit=True,
    )


# --- Assets ----------------------------------------------------------------

_ALLOWED_ASSET_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def _asset_url(filename: str) -> str:
    return f"{settings.DOCS_ASSETS_URL_PREFIX}/screenshots/{filename}"


def _asset_path(filename: str) -> Path:
    # Allow only flat filenames (no separators). Filenames are server-generated
    # on upload so this is mostly to defend the DELETE endpoint.
    if not filename or "/" in filename or "\\" in filename or filename in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid asset filename")
    if not re.match(r"^[A-Za-z0-9._-]+$", filename):
        raise HTTPException(status_code=400, detail="Invalid asset filename")
    root = _assets_root()
    target = (root / filename).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        security_logger.warning("Docs asset path escape attempt: %s", filename)
        raise HTTPException(status_code=400, detail="Invalid asset filename")
    return target


@router.get("/assets", response_model=DocAssetList)
def list_doc_assets(
    current_user: User = Depends(get_current_user),
) -> DocAssetList:
    root = _assets_root()
    items: list[DocAsset] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_file():
            continue
        stat = entry.stat()
        items.append(
            DocAsset(
                filename=entry.name,
                url=_asset_url(entry.name),
                size_bytes=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            )
        )
    return DocAssetList(assets=items)


@router.post("/assets", response_model=DocAsset)
def upload_doc_asset(
    file: UploadFile = File(...),
    current_user: User = Depends(_require_docs_editor),
) -> DocAsset:
    """Upload a screenshot/image for embedding in a documentation page."""
    content_type = (file.content_type or "").lower()
    suffix = _ALLOWED_ASSET_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type (allowed: jpeg, png, webp, gif, svg)",
        )

    root = _assets_root()
    # Preserve a slugified version of the original stem so the file is easy
    # to recognise in the repo while remaining unguessable.
    original_stem = Path(file.filename or "asset").stem.lower()
    safe_stem = re.sub(r"[^a-z0-9-]+", "-", original_stem).strip("-") or "asset"
    safe_stem = safe_stem[:40]
    stored_name = f"{safe_stem}-{secrets.token_hex(6)}{suffix}"
    target = (root / stored_name).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    max_bytes = settings.DOCS_ASSET_MAX_BYTES
    written = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = file.file.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Image exceeds max size")
                out.write(chunk)
    except HTTPException:
        raise
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Could not save asset: {exc}")

    audit_logger.info(
        "Documentation asset uploaded: name=%s bytes=%d by=%s",
        stored_name,
        written,
        current_user.id,
    )
    stat = target.stat()
    return DocAsset(
        filename=stored_name,
        url=_asset_url(stored_name),
        size_bytes=stat.st_size,
        uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    )


@router.delete("/assets/{filename}", status_code=204)
def delete_doc_asset(
    filename: str,
    current_user: User = Depends(_require_docs_editor),
) -> None:
    target = _asset_path(filename)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        target.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not delete asset: {exc}")
    audit_logger.info(
        "Documentation asset deleted: name=%s by=%s",
        filename,
        current_user.id,
    )
