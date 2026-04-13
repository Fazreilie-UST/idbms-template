from typing import Any
from pydantic import BaseModel, Field


class ImportResultResponse(BaseModel):
    message: str
    dry_run: bool = False
    table_name: str | None = None
    filename: str | None = None
    replace_all: bool = False

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    would_insert: int = 0
    would_update: int = 0
    would_unchanged: int = 0

    skipped: int = 0
    duplicates_in_file: int = 0
    total_rows: int = 0
    processed_rows: int = 0

    status: str = "completed"
    import_job_id: int | None = None

    validation_summary: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)