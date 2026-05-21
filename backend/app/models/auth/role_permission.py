from ..base import Base, Column, Integer, ForeignKey

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False, primary_key=True)