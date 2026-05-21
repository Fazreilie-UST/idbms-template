from __future__ import annotations

import hashlib
import json
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_permission
from app.core.rate_limit import limiter
from app.db.deps import get_db
from app.db.session import SessionLocal
from app.models.auth.user import User
from app.models.order.shipping_import_file import (
    ShippingImportFile,
    ShippingImportStatus,
)
from app.services.shipping_import_service import (
    count_shipments_in_file,
    process_import_file,
)


router = APIRouter(prefix="/shipping-imports", tags=["Shipping Imports"])


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


class ShippingImportFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    file_size: int
    content_hash: str | None = None
    status: ShippingImportStatus
    error_message: str | None = None
    summary: dict[str, Any] | None = None
    uploaded_by: UploaderSummary | None = None
    created_at: datetime
    processed_at: datetime | None = None


class ShippingImportUploadResponse(BaseModel):
    record: ShippingImportFileResponse
    duplicate: bool = False


class ShippingImportListResponse(BaseModel):
    items: list[ShippingImportFileResponse]
    total: int
    page: int
    page_size: int


class BatchProcessRequest(BaseModel):
    ids: list[int]


class BatchProcessResult(BaseModel):
    processed: list[ShippingImportFileResponse] = []
    skipped: list[int] = []
    not_found: list[int] = []


class RowCountsResponse(BaseModel):
    counts: dict[int, int]
    not_found: list[int] = []
    skipped: list[int] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_storage_dir() -> Path:
    storage = Path(settings.SHIPPING_IMPORT_DIR).expanduser().resolve()
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def _make_stored_filename(original: str) -> str:
    suffix = Path(original).suffix
    stem = Path(original).stem
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    digest = hashlib.sha1(f"{original}{timestamp}".encode()).hexdigest()[:8]
    safe_stem = "".join(
        c if c.isalnum() or c in ("-", "_", " ") else "_" for c in stem
    ).strip()
    return f"{timestamp}_{digest}_{safe_stem}{suffix}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ShippingImportUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("120/minute")
def upload_shipping_file(
    request: Request,
    file: UploadFile = File(...),
    auto_process: bool = Query(
        False,
        description="If True, parse the file immediately. Defaults to False so "
        "the user can review uploaded files and trigger processing manually.",
    ),
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    """Upload a shipping Excel file (Master Board Tracker layout).

    Files are stored on disk in ``SHIPPING_IMPORT_DIR`` and persisted in the
    ``shipping_import_files`` table in ``pending`` state. Files with the exact
    same bytes as an existing upload are deduplicated.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    storage_dir = _ensure_storage_dir()
    stored_name = _make_stored_filename(file.filename)
    target_path = storage_dir / stored_name

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

    existing = (
        db.query(ShippingImportFile)
        .filter(ShippingImportFile.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        target_path.unlink(missing_ok=True)
        return ShippingImportUploadResponse(
            record=ShippingImportFileResponse.model_validate(existing),
            duplicate=True,
        )

    record = ShippingImportFile(
        original_filename=file.filename,
        stored_filename=stored_name,
        storage_path=str(target_path),
        file_size=bytes_written,
        content_hash=content_hash,
        status=ShippingImportStatus.pending,
        uploaded_by_id=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if auto_process:
        process_import_file(db, record)
        db.refresh(record)

    return ShippingImportUploadResponse(
        record=ShippingImportFileResponse.model_validate(record),
        duplicate=False,
    )


@router.get("", response_model=ShippingImportListResponse)
def list_shipping_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ShippingImportStatus | None = Query(None, alias="status"),
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    query = db.query(ShippingImportFile)
    if status_filter is not None:
        query = query.filter(ShippingImportFile.status == status_filter)

    total = query.count()
    items = (
        query.order_by(desc(ShippingImportFile.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ShippingImportListResponse(
        items=[ShippingImportFileResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{file_id}", response_model=ShippingImportFileResponse)
def get_shipping_file(
    file_id: int,
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    record = (
        db.query(ShippingImportFile)
        .filter(ShippingImportFile.id == file_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Import file not found")
    return record


@router.post("/process", response_model=BatchProcessResult)
def process_shipping_files(
    payload: BatchProcessRequest,
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    """Run the parser for one or more uploaded files.

    Only files currently in ``pending`` or ``failed`` state are processed;
    others are reported in ``skipped``.
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
            db.query(ShippingImportFile)
            .filter(ShippingImportFile.id == file_id)
            .first()
        )
        if not record:
            result.not_found.append(file_id)
            continue
        if record.status not in (
            ShippingImportStatus.pending,
            ShippingImportStatus.failed,
        ):
            result.skipped.append(file_id)
            continue

        process_import_file(db, record)
        db.refresh(record)
        result.processed.append(
            ShippingImportFileResponse.model_validate(record)
        )

    return result


@router.post("/row-counts", response_model=RowCountsResponse)
def get_shipping_row_counts(
    payload: BatchProcessRequest,
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    """Return the number of shipment rows each uploaded file contains.

    Used by the frontend to size the per-row progress bar. Files already in
    ``success`` state are reported in ``skipped``.
    """
    if not payload.ids:
        raise HTTPException(status_code=400, detail="ids is required")

    counts: dict[int, int] = {}
    not_found: list[int] = []
    skipped: list[int] = []
    for file_id in payload.ids:
        record = (
            db.query(ShippingImportFile)
            .filter(ShippingImportFile.id == file_id)
            .first()
        )
        if not record:
            not_found.append(file_id)
            continue
        if record.status == ShippingImportStatus.success:
            skipped.append(file_id)
            continue
        counts[file_id] = count_shipments_in_file(Path(record.storage_path))

    return RowCountsResponse(
        counts=counts, not_found=not_found, skipped=skipped
    )


@router.post("/{file_id}/process-stream")
def process_shipping_file_stream(
    file_id: int,
    current_user: User = Depends(require_permission("shipping:import")),
):
    """Process a single import file and stream per-row progress events back
    to the client as newline-delimited JSON.

    Event shapes:
      {"event": "init",         "file_id": N, "total": T}
      {"event": "row_done",     "file_id": N, "processed": i, "total": T,
                                "config_number": "...", "tracking": "...",
                                "sheet": "..."}
      {"event": "row_skipped",  "file_id": N, "processed": i, "total": T,
                                "reason": "duplicate", ...}
      {"event": "sheet_skipped","file_id": N, "processed": i, "total": T,
                                "sheet": "...", "reason": "no_header"}
      {"event": "complete",     "file_id": N, "record": {...}}
      {"event": "error",        "file_id": N, "message": "..."}
    """

    def _event_stream():
        session = SessionLocal()
        try:
            record = (
                session.query(ShippingImportFile)
                .filter(ShippingImportFile.id == file_id)
                .first()
            )
            if not record:
                yield json.dumps(
                    {
                        "event": "error",
                        "file_id": file_id,
                        "message": "Import file not found",
                    }
                ) + "\n"
                return
            if record.status not in (
                ShippingImportStatus.pending,
                ShippingImportStatus.failed,
            ):
                yield json.dumps(
                    {
                        "event": "error",
                        "file_id": file_id,
                        "message": f"File is in '{record.status.value}' state and cannot be processed",
                    }
                ) + "\n"
                return

            state = {"total": 0, "processed": 0}
            event_queue: "queue.Queue[str | None]" = queue.Queue()

            def emit(event_name: str, payload: dict[str, Any]) -> None:
                if event_name == "init":
                    state["total"] = int(payload.get("total", 0))
                elif event_name in ("row_done", "row_skipped"):
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
                except Exception as exc:  # noqa: BLE001
                    worker_error["message"] = f"{type(exc).__name__}: {exc}"
                finally:
                    event_queue.put(None)

            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()

            heartbeat_interval = 2.0
            while True:
                try:
                    item = event_queue.get(timeout=heartbeat_interval)
                except queue.Empty:
                    yield " \n"
                    continue
                if item is None:
                    break
                yield item

            thread.join()

            if worker_error:
                yield json.dumps(
                    {
                        "event": "error",
                        "file_id": file_id,
                        "message": worker_error["message"],
                    }
                ) + "\n"
                return

            session.refresh(record)
            yield json.dumps(
                {
                    "event": "complete",
                    "file_id": file_id,
                    "record": ShippingImportFileResponse.model_validate(
                        record
                    ).model_dump(mode="json"),
                }
            ) + "\n"
        finally:
            session.close()

    response = StreamingResponse(
        _event_stream(), media_type="application/x-ndjson"
    )
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Cache-Control"] = "no-cache"
    return response


@router.post("/{file_id}/reprocess", response_model=ShippingImportFileResponse)
def reprocess_shipping_file(
    file_id: int,
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    record = (
        db.query(ShippingImportFile)
        .filter(ShippingImportFile.id == file_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Import file not found")

    process_import_file(db, record)
    db.refresh(record)
    return record


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipping_file(
    file_id: int,
    delete_file: bool = Query(True, description="Also delete the file from disk"),
    current_user: User = Depends(require_permission("shipping:import")),
    db: Session = Depends(get_db),
):
    record = (
        db.query(ShippingImportFile)
        .filter(ShippingImportFile.id == file_id)
        .first()
    )
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
