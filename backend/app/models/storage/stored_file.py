from ..base import Base, Column, Integer, String, BigInteger, DateTime, ForeignKey, relationship, func

class StoredFile(Base):
    __tablename__ = "stored_file"

    file_id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    storage_path = Column(String(1000), nullable=False, unique=True)
    file_extension = Column(String(20), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=True)

    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    uploaded_by = relationship("User")
    import_jobs = relationship("ImportJob", back_populates="stored_file")