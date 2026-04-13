from sqlalchemy.orm import relationship

from ..base import Base, Column, Integer, String

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

    import_jobs = relationship("ImportJob", back_populates="imported_by")
    stored_files = relationship("StoredFile", back_populates="uploaded_by")