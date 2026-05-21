from ..base import Base, Column, Integer, String, ForeignKey, relationship

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False) # Example: build_plan:create <module>:<action>
    name = Column(String, nullable=False) # Example: Create Build Plan
    description = Column(String, nullable= True)
    action_category_id = Column(Integer, ForeignKey("action_categories.id"), nullable=False)

    action_category = relationship("ActionCategory", back_populates="permissions")
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

"""
permission codes

build_plan:create
build_plan:read
build_plan:update
build_plan:send
build_plan:lock
build_plan:revise

build_request:create
build_request:update
build_request:approve
build_request:cancel

shipping:create
shipping:update
shipping:read

user:manage
role:manage

"""