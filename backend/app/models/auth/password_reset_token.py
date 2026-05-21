from ..base import Base, Column, Integer, String, Boolean, DateTime, ForeignKey

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    token_hash = Column(String)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)