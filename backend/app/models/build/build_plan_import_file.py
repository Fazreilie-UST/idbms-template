import enum

from ..base import (
    Base,
    Column,
    Integer,
    String,
    Text,
    BigInteger,
    DateTime,
    ForeignKey,
    Enum,
    Index,
    JSON,
    relationship,
    func,
)


class BuildPlanImportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class BuildPlanImportFile(Base):
    """Tracks build plan Excel files uploaded by PMs for bulk historical import."""

    __tablename__ = "build_plan_import_files"

    id = Column(Integer, primary_key=True, index=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    storage_path = Column(String(1000), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)  # sha256 hex digest

    # Parsed from filename: e.g. "LzP Build Plan WW1626 rev1.xlsx" -> ww=16, year=2026, file_revision=1
    work_week = Column(Integer, nullable=True)
    work_year = Column(Integer, nullable=True)
    file_revision = Column(Integer, nullable=True)

    status = Column(
        Enum(BuildPlanImportStatus, name="buildplanimportstatus"),
        nullable=False,
        default=BuildPlanImportStatus.pending,
    )
    error_message = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True)  # { build_plans_created, build_requests_created, unrecorded_users: [...] }

    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    shipping_infos = relationship(
        "BuildPlanImportShippingInfo",
        back_populates="import_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    si_rows = relationship(
        "BuildPlanImportSi",
        back_populates="import_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_build_plan_import_files_status", "status"),
        Index("ix_build_plan_import_files_created_at", "created_at"),
    )
