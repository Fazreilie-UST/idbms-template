import hashlib
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.storage.stored_file import StoredFile


class FileStorageService:
    def __init__(self, db: Session, base_dir: str = "storage/imports"):
        self.db = db
        self.base_dir = Path(base_dir)

    def save_uploaded_file(
        self,
        content: bytes,
        original_filename: str,
        mime_type: str | None = None,
        uploaded_by_id: int | None = None,
    ) -> StoredFile:
        now = datetime.now(UTC)
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid4().hex}{ext}"

        relative_dir = Path(str(now.year), f"{now.month:02d}", f"{now.day:02d}")
        full_dir = self.base_dir / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)

        full_path = full_dir / unique_name
        full_path.write_bytes(content)

        checksum = hashlib.sha256(content).hexdigest()

        stored_file = StoredFile(
            original_filename=original_filename,
            stored_filename=unique_name,
            storage_path=str(full_path),
            file_extension=ext,
            mime_type=mime_type,
            file_size=len(content),
            checksum=checksum,
            uploaded_by_id=uploaded_by_id,
        )

        self.db.add(stored_file)
        self.db.flush()
        return stored_file

    def delete_stored_file(self, stored_file: StoredFile) -> None:
        path = Path(stored_file.storage_path)

        if path.exists():
            path.unlink()

        self.db.delete(stored_file)
        self.db.flush()