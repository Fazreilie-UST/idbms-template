"""Shared helpers for stock import services (dimension + fact)."""
from typing import Any

from sqlalchemy.orm import Session

from app.models.stock.import_job import ImportJob


def should_log_import(result: dict[str, Any]) -> bool:
    if result.get("dry_run", False):
        return False
    return (result.get("inserted", 0) > 0) or (result.get("updated", 0) > 0)


def log_import_job(
    db: Session,
    result: dict[str, Any],
    imported_by_id: int | None = None,
    file_id: int | None = None,
) -> ImportJob:
    job = ImportJob(
        table_name=result.get("table_name"),
        filename=result.get("filename"),
        file_type="csv",
        replace_all=result.get("replace_all", False),
        inserted=result.get("inserted", 0),
        updated=result.get("updated", 0),
        unchanged=result.get("unchanged", 0),
        skipped=result.get("skipped", 0),
        duplicates_in_file=result.get("duplicates_in_file", 0),
        total_rows=result.get("total_rows", 0),
        processed_rows=result.get("processed_rows", 0),
        status=result.get("status", "completed"),
        message=result.get("message"),
        imported_by_id=imported_by_id,
        file_id=file_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
