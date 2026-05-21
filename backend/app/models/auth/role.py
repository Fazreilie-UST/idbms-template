from ..base import Base, Column, Integer, String, relationship

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable= True)

    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")

"""
Normal User
Program Manager
Requestor
ODM (KIV)
Coordinator
"""