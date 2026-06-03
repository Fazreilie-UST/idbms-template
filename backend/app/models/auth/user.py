from ..base import Base, Column, Integer, String, Boolean, DateTime, ForeignKey, relationship, func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, nullable=False, primary_key=True, index=True)
    employee_id = Column(String, nullable=True, unique=True) # make nullable=False later
    email = Column(String, nullable=True, unique=True, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # make nullable=False later
    is_active = Column(Boolean, nullable=False, default=False) # make default=False later
    can_login = Column(Boolean, nullable=False, default=False)
    token_version = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_ = Column(DateTime, nullable=True) # make default=False later
    legacy_ref = Column(String, nullable=True, unique=True)

    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    profile_picture_url = Column(String, nullable=True)

    department = relationship("Department", back_populates="users")
    roles = relationship("Role", secondary="user_roles", back_populates="users")

    stored_files = relationship("StoredFile", back_populates="uploaded_by")