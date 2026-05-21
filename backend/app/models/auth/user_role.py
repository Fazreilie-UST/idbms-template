from ..base import Base, Column, Integer, ForeignKey

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, primary_key=True)