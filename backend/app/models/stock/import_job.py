from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Enum as SqlEnum, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.stock.enums import ImportExportTableName, FileType


class ImportJob(Base):
    __tablename__ = "import_job"

    import_job_id = Column(Integer, primary_key=True, index=True)

    table_name = Column(SqlEnum(ImportExportTableName, name="import_table_name_enum"), nullable=False)
    filename = Column(String, nullable=True)
    file_type = Column(SqlEnum(FileType, name="file_type_enum"), nullable=False, default=FileType.CSV)

    replace_all = Column(Boolean, nullable=False, default=False)

    inserted = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=0)
    unchanged = Column(Integer, nullable=False, default=0)

    skipped = Column(Integer, nullable=False, default=0)
    duplicates_in_file = Column(Integer, nullable=False, default=0)
    total_rows = Column(Integer, nullable=False, default=0)
    processed_rows = Column(Integer, nullable=False, default=0)

    status = Column(String, nullable=False, default="completed")
    message = Column(String, nullable=True)

    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    imported_by = relationship("User", back_populates="import_jobs")
    file_id = Column(Integer, ForeignKey("stored_file.file_id"), nullable=True)
    stored_file = relationship("StoredFile", back_populates="import_jobs")