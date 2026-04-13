from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.stock.import_job import ImportJob


router = APIRouter(prefix="/imports", tags=["stock-imports"])


@router.get("/{import_job_id}/file")
def download_import_file(
    import_job_id: int,
    db: Session = Depends(get_db),
):
    job = db.query(ImportJob).filter(ImportJob.import_job_id == import_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    if not job.stored_file:
        raise HTTPException(status_code=404, detail="No file attached to this import job")

    path = Path(job.stored_file.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found on disk")

    return FileResponse(
        path=str(path),
        media_type=job.stored_file.mime_type or "text/csv",
        filename=job.stored_file.original_filename,
    )

@router.get("/history")
def get_import_history(
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ImportJob).order_by(ImportJob.created_at.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "import_job_id": item.import_job_id,
                "table_name": item.table_name,
                "filename": item.filename,
                "file_id": item.file_id,
                "has_file": item.stored_file is not None,
                "inserted": item.inserted,
                "updated": item.updated,
                "unchanged": item.unchanged,
                "status": item.status,
                "message": item.message,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }