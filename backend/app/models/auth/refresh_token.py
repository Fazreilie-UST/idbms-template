from ..base import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    relationship,
    func,
)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    token_hash = Column(String, nullable=False, unique=True, index=True)

    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)

    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")