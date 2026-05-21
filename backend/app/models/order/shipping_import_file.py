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


class ShippingImportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class ShippingImportFile(Base):
    """Tracks shipping Excel files uploaded by PMs for bulk shipment import."""

    __tablename__ = "shipping_import_files"

    id = Column(Integer, primary_key=True, index=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    storage_path = Column(String(1000), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)  # sha256 hex digest

    status = Column(
        Enum(ShippingImportStatus, name="shippingimportstatus"),
        nullable=False,
        default=ShippingImportStatus.pending,
    )
    error_message = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True)
    # { sheets_processed, sheets_skipped, inserted, skipped_duplicate, missing_user, missing_recipients: [...] }

    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    __table_args__ = (
        Index("ix_shipping_import_files_status", "status"),
        Index("ix_shipping_import_files_created_at", "created_at"),
    )
