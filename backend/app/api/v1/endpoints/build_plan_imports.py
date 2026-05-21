from __future__ import annotations

import hashlib
import json
import queue
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.dependencies import require_permission
from app.core.rate_limit import limiter
from app.db.deps import get_db
from app.db.session import SessionLocal
from app.models.auth.user import User
from app.models.build.build_plan_import_file import (
    BuildPlanImportFile,
    BuildPlanImportStatus,
)
from app.models.build.build_plan_import_shipping_info import (
    BuildPlanImportShippingInfo,
)
from app.models.build.build_plan_import_si import BuildPlanImportSi
from app.models.build.family import Family
from app.models.build.pm_family import PMFamily
from app.services.build_plan_import_service import (
    count_build_plans_in_file,
    parse_filename_metadata,
    process_import_file,
)
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/build-plan-imports", tags=["Build Plan Imports"])


ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UploaderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None = None
    email: str | None = None


class BuildPlanImportFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    file_size: int
    content_hash: str | None = None
    work_week: int | None = None
    work_year: int | None = None
    file_revision: int | None = None
    status: BuildPlanImportStatus
    error_message: str | None = None
    summary: dict[str, Any] | None = None
    uploaded_by: UploaderSummary | None = None
    created_at: datetime
    processed_at: datetime | None = None


class BuildPlanImportUploadResponse(BaseModel):
    """Upload result; ``duplicate`` flags that the file's bytes match an
    existing import (in which case ``record`` points to the *existing* row
    and the freshly uploaded file is discarded)."""
    record: BuildPlanImportFileResponse
    duplicate: bool = False


class BuildPlanImportListResponse(BaseModel):
    items: list[BuildPlanImportFileResponse]
    total: int
    page: int
    page_size: int


class BatchProcessRequest(BaseModel):
    ids: list[int]


class BatchProcessResult(BaseModel):
    processed: list[BuildPlanImportFileResponse] = []
    skipped: list[int] = []  # ids that were not in pending/failed state
    not_found: list[int] = []


class PlanCountsResponse(BaseModel):
    counts: dict[int, int]
    not_found: list[int] = []
    skipped: list[int] = []  # already processed (success)


class BuildPlanImportShippingInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_index: int | None = None
    responsibility: str | None = None
    name: str | None = None
    address: str | None = None


class BuildPlanImportSiRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_index: int | None = None
    si_description: str | None = None
    si_lot_numbers: str | None = None
    class_test_rev: str | None = None
    request_qty: int | None = None
    request_dock_date: str | None = None
    commit_qty: int | None = None
    commit_dock_date: str | None = None
    actual_qty: int | None = None
    actual_dock_date: str | None = None
    comments: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_storage_dir() -> Path:
    storage = Path(settings.BUILD_PLAN_IMPORT_DIR).expanduser().resolve()
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def _make_stored_filename(original: str) -> str:
    suffix = Path(original).suffix
    stem = Path(original).stem
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    digest = hashlib.sha1(f"{original}{timestamp}".encode()).hexdigest()[:8]
    # Safe-ish filename
    safe_stem = "".join(c if c.isalnum() or c in ("-", "_", " ") else "_" for c in stem).strip()
    return f"{timestamp}_{digest}_{safe_stem}{suffix}"


def _extract_family_code_from_filename(filename: str) -> str | None:
    """Pull the family code prefix from a build-plan filename, e.g.
    "LzP Build Plan WW3325 Rev01.xlsx" -> "LzP".

    Returns the first whitespace-delimited token of the stem when it looks
    like a family code (alphanumeric, <= 8 chars). Returns ``None`` when no
    plausible prefix can be extracted so the caller can fall back to
    permissive behaviour rather than rejecting on a parser quirk.
    """
    stem = Path(filename or "").stem.strip()
    if not stem:
        return None
    token = stem.split()[0] if stem.split() else ""
    if not token or len(token) > 8 or not token.replace("_", "").isalnum():
        return None
    return token


def _is_admin(user: User) -> bool:
    return "Admin" in RBACService.get_user_roles(user)


def _user_has_family(db: Session, user_id: int, family_id: int) -> bool:
    return (
        db.query(PMFamily.id)
        .filter(PMFamily.user_id == user_id, PMFamily.family_id == family_id)
        .first()
        is not None
    )


def _enforce_family_upload_permission(
    db: Session, user: User, filename: str
) -> None:
    """Reject the upload when a non-admin PM tries to upload a file whose
    filename references a family they are not assigned to.

    If the family code cannot be confidently extracted from the filename, or
    the prefix doesn't match any known family, the upload is allowed so a
    parser quirk doesn't block legitimate work. Admins always bypass.
    """
    if _is_admin(user):
        return

    code = _extract_family_code_from_filename(filename)
    if not code:
        return  # filename not parseable; let through

    family = db.query(Family).filter(Family.code.ilike(code)).first()
    if family is None:
        return  # unknown family code; let through

    if not _user_has_family(db, user.id, family.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You are not assigned to family '{family.code}'. Ask an "
                f"administrator to map your account to this family in "
                f"the PM-Family table before uploading."
            ),
        )


def _ensure_can_process(record: BuildPlanImportFile, user: User) -> None:
    """Only the uploader (or an Admin) may process / reprocess a file."""
    if _is_admin(user):
        return
    if record.uploaded_by_id is None:
        # Legacy rows with no uploader: only admins can process.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This file has no recorded uploader; only an admin can process it.",
        )
    if record.uploaded_by_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the PM who uploaded this file may process it.",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BuildPlanImportUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
# Generous limit so PMs can drag-drop a folder of historical build plans in
# one go without tripping rate limiting. The expensive work (parsing) is
# gated by the separate /process endpoint. Endpoint is auth + permission
# gated and uploads are capped at MAX_UPLOAD_BYTES, so abuse risk is low.
# Tighten (e.g. "30/minute") for production if needed.
@limiter.limit("600/minute")
def upload_build_plan_file(
    request: Request,
    file: UploadFile = File(...),
    auto_process: bool = Query(
        False,
        description="If True, parse the file immediately. Defaults to False so the "
                    "user can review uploaded files and trigger processing manually.",
    ),
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Upload a build plan Excel file.

    Workflow:
      1. Stream the file to disk while computing its SHA-256.
      2. If a previous upload has the *exact same bytes* (same content hash),
         discard the new file and return the existing record with
         ``duplicate=True`` so the UI can warn the user.
      3. Otherwise persist a ``BuildPlanImportFile`` row in ``pending`` state.
      4. Only run the parser when ``auto_process=True`` (default: False).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Block non-admin PMs from uploading files for families they don't own.
    _enforce_family_upload_permission(db, current_user, file.filename)

    storage_dir = _ensure_storage_dir()
    stored_name = _make_stored_filename(file.filename)
    target_path = storage_dir / stored_name

    # Stream to disk while enforcing size limit and computing hash.
    bytes_written = 0
    hasher = hashlib.sha256()
    try:
        with target_path.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    out.close()
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds max size of {MAX_UPLOAD_BYTES} bytes",
                    )
                hasher.update(chunk)
                out.write(chunk)
    finally:
        file.file.close()

    content_hash = hasher.hexdigest()

    # Duplicate check
    existing = (
        db.query(BuildPlanImportFile)
        .filter(BuildPlanImportFile.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        # Discard the just-written file; keep the original on disk.
        target_path.unlink(missing_ok=True)
        return BuildPlanImportUploadResponse(
            record=BuildPlanImportFileResponse.model_validate(existing),
            duplicate=True,
        )

    metadata = parse_filename_metadata(file.filename)

    # Pre-compute the build-plan column count so the first batch run can
    # render the progress total without re-parsing the workbook. Failures
    # here are non-fatal (the count will be recomputed lazily on demand).
    try:
        plan_count = count_build_plans_in_file(target_path)
    except Exception:  # noqa: BLE001
        plan_count = None

    record = BuildPlanImportFile(
        original_filename=file.filename,
        stored_filename=stored_name,
        storage_path=str(target_path),
        file_size=bytes_written,
        content_hash=content_hash,
        work_week=metadata["work_week"],
        work_year=metadata["work_year"],
        file_revision=metadata["file_revision"],
        status=BuildPlanImportStatus.pending,
        uploaded_by_id=current_user.id,
        summary={"plan_count": plan_count} if plan_count is not None else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if auto_process:
        process_import_file(db, record)
        db.refresh(record)

    return BuildPlanImportUploadResponse(
        record=BuildPlanImportFileResponse.model_validate(record),
        duplicate=False,
    )


@router.get("", response_model=BuildPlanImportListResponse)
def list_build_plan_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: BuildPlanImportStatus | None = Query(None, alias="status"),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    mine: bool = Query(
        False,
        description=(
            "When true, only return files uploaded by the current user. "
            "Useful for the 'Imported By Me' tab in the UI."
        ),
    ),
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    query = db.query(BuildPlanImportFile).options(
        joinedload(BuildPlanImportFile.uploaded_by)
    )
    if status_filter is not None:
        query = query.filter(BuildPlanImportFile.status == status_filter)
    if mine:
        query = query.filter(BuildPlanImportFile.uploaded_by_id == current_user.id)

    total = query.count()

    # Map UI column keys -> orderable expressions. Anything not listed falls
    # back to created_at desc to preserve historical behavior.
    direction = asc if sort_order == "asc" else desc
    sort_map = {
        "original_filename": [BuildPlanImportFile.original_filename],
        "status": [BuildPlanImportFile.status],
        "created_at": [BuildPlanImportFile.created_at],
        "processed_at": [BuildPlanImportFile.processed_at],
        # Composite chronological key matching the UI's "WW / Year / Rev" col.
        "ww": [
            BuildPlanImportFile.work_year,
            BuildPlanImportFile.work_week,
            BuildPlanImportFile.file_revision,
        ],
        "uploaded_by": [User.full_name, User.email],
    }
    cols = sort_map.get(sort_by) if sort_by else None
    if cols:
        if sort_by == "uploaded_by":
            query = query.outerjoin(User, BuildPlanImportFile.uploaded_by_id == User.id)
        query = query.order_by(*[direction(c) for c in cols], desc(BuildPlanImportFile.id))
    else:
        query = query.order_by(desc(BuildPlanImportFile.created_at), desc(BuildPlanImportFile.id))

    items = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return BuildPlanImportListResponse(
        items=[BuildPlanImportFileResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{file_id}", response_model=BuildPlanImportFileResponse)
def get_build_plan_file(
    file_id: int,
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    record = db.query(BuildPlanImportFile).filter(BuildPlanImportFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import file not found")
    return record


class BuildPlanImportMetadataUpdate(BaseModel):
    """Partial-update payload for manually correcting filename-derived metadata
    when the auto-parser couldn't extract it (e.g. unusual filename format)."""

    work_week: int | None = None
    work_year: int | None = None
    file_revision: int | None = None


@router.patch("/{file_id}", response_model=BuildPlanImportFileResponse)
def update_build_plan_file_metadata(
    file_id: int,
    payload: BuildPlanImportMetadataUpdate,
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Manually override work_week / work_year / file_revision for an import
    file. Useful when the filename doesn't match the auto-parser. Also resets
    a `skipped` row back to `pending` so it can be processed again."""
    record = db.query(BuildPlanImportFile).filter(BuildPlanImportFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import file not found")

    if payload.work_week is not None:
        if payload.work_week < 1 or payload.work_week > 53:
            raise HTTPException(status_code=400, detail="work_week must be 1..53")
        record.work_week = payload.work_week
    if payload.work_year is not None:
        if payload.work_year < 2000 or payload.work_year > 2099:
            raise HTTPException(status_code=400, detail="work_year must be 2000..2099")
        record.work_year = payload.work_year
    if payload.file_revision is not None:
        if payload.file_revision < 0:
            raise HTTPException(status_code=400, detail="file_revision must be >= 0")
        record.file_revision = payload.file_revision

    # If the row was skipped purely because metadata was missing and we now
    # have all three fields, flip it back to pending so the user can process.
    if (
        record.status == BuildPlanImportStatus.skipped
        and record.work_week is not None
        and record.work_year is not None
        and record.file_revision is not None
    ):
        record.status = BuildPlanImportStatus.pending
        record.error_message = None

    db.commit()
    db.refresh(record)
    return record


@router.post("/process", response_model=BatchProcessResult)
def process_build_plan_files(
    payload: BatchProcessRequest,
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Run the parser for one or more uploaded files.

    Only files currently in ``pending`` or ``failed`` state will be processed;
    others are reported in ``skipped``. Each file is parsed in its own unit of
    work so a single bad file does not abort the batch.
    """
    if not payload.ids:
        raise HTTPException(status_code=400, detail="ids is required")

    result = BatchProcessResult()
    seen: set[int] = set()
    for file_id in payload.ids:
        if file_id in seen:
            continue
        seen.add(file_id)

        record = (
            db.query(BuildPlanImportFile)
            .filter(BuildPlanImportFile.id == file_id)
            .first()
        )
        if not record:
            result.not_found.append(file_id)
            continue
        try:
            _ensure_can_process(record, current_user)
        except HTTPException:
            # File belongs to a different PM; surface as skipped so a batch
            # request with mixed ownership still completes for the caller's
            # own files.
            result.skipped.append(file_id)
            continue
        if record.status not in (
            BuildPlanImportStatus.pending,
            BuildPlanImportStatus.failed,
        ):
            result.skipped.append(file_id)
            continue

        process_import_file(db, record)
        db.refresh(record)
        result.processed.append(BuildPlanImportFileResponse.model_validate(record))

    return result


@router.post("/plan-counts", response_model=PlanCountsResponse)
def get_build_plan_counts(
    payload: BatchProcessRequest,
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Return the number of build-plan columns each uploaded file contains.

    Used by the frontend to size the per-build-plan progress bar before kicking
    off processing. Files already in ``success`` state are reported in
    ``skipped`` so the UI can exclude them from the denominator.
    """
    if not payload.ids:
        raise HTTPException(status_code=400, detail="ids is required")

    counts: dict[int, int] = {}
    not_found: list[int] = []
    skipped: list[int] = []
    dirty = False
    for file_id in payload.ids:
        record = (
            db.query(BuildPlanImportFile)
            .filter(BuildPlanImportFile.id == file_id)
            .first()
        )
        if not record:
            not_found.append(file_id)
            continue
        if record.status == BuildPlanImportStatus.success:
            skipped.append(file_id)
            continue

        # Plan count is a pure function of the file bytes (which are immutable
        # once uploaded), so cache it on the record's ``summary`` JSON. This
        # turns a re-parse of every selected file into a free lookup for any
        # subsequent batch — critical when the user selects 20+ files at once.
        cached = (record.summary or {}).get("plan_count") if record.summary else None
        if isinstance(cached, int):
            counts[file_id] = cached
            continue

        plan_count = count_build_plans_in_file(Path(record.storage_path))
        counts[file_id] = plan_count
        new_summary = dict(record.summary or {})
        new_summary["plan_count"] = plan_count
        record.summary = new_summary
        dirty = True

    if dirty:
        db.commit()

    return PlanCountsResponse(counts=counts, not_found=not_found, skipped=skipped)


@router.post("/{file_id}/process-stream")
def process_build_plan_file_stream(
    file_id: int,
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Process a single import file and stream per-build-plan progress events
    back to the client as newline-delimited JSON.

    Event shapes (one per line):
      {"event": "init",         "file_id": N, "total": T}
      {"event": "plan_done",    "file_id": N, "processed": i, "total": T,
                                   "config_number": "...", "family": "...", "sku": "..."}
      {"event": "plan_skipped", "file_id": N, "processed": i, "total": T,
                                   "reason": "empty" | "missing_config_number"}
      {"event": "sheet_skipped","file_id": N, "processed": i, "total": T,
                                   "sheet": "...",   "columns": K}
      {"event": "complete",     "file_id": N, "record": {...}}
      {"event": "error",        "file_id": N, "message": "..."}
    """
    # Authorization: only the uploader (or an Admin) may process. We use the
    # request-scoped session here purely for the pre-check; the streaming
    # body opens its own SessionLocal as before.
    pre_record = (
        db.query(BuildPlanImportFile)
        .filter(BuildPlanImportFile.id == file_id)
        .first()
    )
    if not pre_record:
        raise HTTPException(status_code=404, detail="Import file not found")
    _ensure_can_process(pre_record, current_user)
    # We deliberately use a fresh Session that lives for the lifetime of the
    # generator instead of relying on Depends(get_db). FastAPI closes the
    # request-scoped session as soon as the endpoint function returns, which
    # for a StreamingResponse happens before the generator runs.
    def _event_stream():
        session = SessionLocal()
        try:
            record = (
                session.query(BuildPlanImportFile)
                .filter(BuildPlanImportFile.id == file_id)
                .first()
            )
            if not record:
                yield json.dumps({"event": "error", "file_id": file_id,
                                  "message": "Import file not found"}) + "\n"
                return
            if record.status not in (
                BuildPlanImportStatus.pending,
                BuildPlanImportStatus.failed,
            ):
                yield json.dumps({
                    "event": "error",
                    "file_id": file_id,
                    "message": f"File is in '{record.status.value}' state and cannot be processed",
                }) + "\n"
                return

            state = {"total": 0, "processed": 0}
            # Use a thread-safe queue so the parsing thread can hand events
            # over to the streaming generator as they happen, instead of
            # buffering them until the whole file has finished processing.
            event_queue: "queue.Queue[str | None]" = queue.Queue()

            def emit(event_name: str, payload: dict[str, Any]) -> None:
                if event_name == "init":
                    state["total"] = int(payload.get("total", 0))
                else:
                    state["processed"] += 1
                event = {
                    "event": event_name,
                    "file_id": file_id,
                    "processed": state["processed"],
                    "total": state["total"],
                    **payload,
                }
                event_queue.put(json.dumps(event) + "\n")

            worker_error: dict[str, str] = {}

            def _worker() -> None:
                try:
                    process_import_file(session, record, progress_cb=emit)
                except Exception as exc:  # noqa: BLE001 - report through the stream
                    worker_error["message"] = f"{type(exc).__name__}: {exc}"
                finally:
                    # Sentinel: tells the generator the worker has finished.
                    event_queue.put(None)

            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()

            # Heartbeat: yield a no-op every few seconds so any intermediate
            # buffer is forced to flush even when the worker is between events
            # (e.g. opening the workbook or reading a large sheet).
            heartbeat_interval = 2.0
            while True:
                try:
                    item = event_queue.get(timeout=heartbeat_interval)
                except queue.Empty:
                    yield " \n"  # whitespace-only line; client parser ignores it
                    continue
                if item is None:
                    break
                yield item

            thread.join()

            if worker_error:
                yield json.dumps({
                    "event": "error",
                    "file_id": file_id,
                    "message": worker_error["message"],
                }) + "\n"
                return

            session.refresh(record)
            yield json.dumps({
                "event": "complete",
                "file_id": file_id,
                "record": BuildPlanImportFileResponse.model_validate(record).model_dump(
                    mode="json"
                ),
            }) + "\n"
        finally:
            session.close()

    response = StreamingResponse(_event_stream(), media_type="application/x-ndjson")
    # Disable buffering at proxies (nginx) so events arrive in real time.
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Cache-Control"] = "no-cache"
    return response


@router.post("/{file_id}/reprocess", response_model=BuildPlanImportFileResponse)
def reprocess_build_plan_file(
    file_id: int,
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    record = db.query(BuildPlanImportFile).filter(BuildPlanImportFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import file not found")

    _ensure_can_process(record, current_user)

    process_import_file(db, record)
    db.refresh(record)
    return record


@router.get(
    "/{file_id}/shipping-infos",
    response_model=list[BuildPlanImportShippingInfoResponse],
)
def list_build_plan_file_shipping_infos(
    file_id: int,
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Return rows parsed from the file's ``Shipping Info`` sheet."""
    if not db.query(BuildPlanImportFile.id).filter(
        BuildPlanImportFile.id == file_id
    ).first():
        raise HTTPException(status_code=404, detail="Import file not found")

    rows = (
        db.query(BuildPlanImportShippingInfo)
        .filter(BuildPlanImportShippingInfo.import_file_id == file_id)
        .order_by(BuildPlanImportShippingInfo.row_index.asc().nullslast(),
                  BuildPlanImportShippingInfo.id.asc())
        .limit(limit)
        .all()
    )
    return [BuildPlanImportShippingInfoResponse.model_validate(r) for r in rows]


@router.get(
    "/{file_id}/si-rows",
    response_model=list[BuildPlanImportSiRowResponse],
)
def list_build_plan_file_si_rows(
    file_id: int,
    limit: int = Query(5000, ge=1, le=20000),
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    """Return rows parsed from the file's ``Si`` sheet."""
    if not db.query(BuildPlanImportFile.id).filter(
        BuildPlanImportFile.id == file_id
    ).first():
        raise HTTPException(status_code=404, detail="Import file not found")

    rows = (
        db.query(BuildPlanImportSi)
        .filter(BuildPlanImportSi.import_file_id == file_id)
        .order_by(BuildPlanImportSi.row_index.asc().nullslast(),
                  BuildPlanImportSi.id.asc())
        .limit(limit)
        .all()
    )
    return [BuildPlanImportSiRowResponse.model_validate(r) for r in rows]


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_build_plan_file(
    file_id: int,
    delete_file: bool = Query(True, description="Also delete the file from disk"),
    current_user: User = Depends(require_permission("build_plan:import")),
    db: Session = Depends(get_db),
):
    record = db.query(BuildPlanImportFile).filter(BuildPlanImportFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import file not found")

    storage_path = Path(record.storage_path)
    db.delete(record)
    db.commit()

    if delete_file and storage_path.exists():
        try:
            storage_path.unlink()
        except OSError:
            pass

    return None
