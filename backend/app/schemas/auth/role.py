from pydantic import BaseModel


class RoleBase(BaseModel):
    role_name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role_name: str | None = None
    description: str | None = None


class PermissionMini(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class RoleResponse(RoleBase):
    id: int
    permissions: list[PermissionMini] = []

    model_config = {"from_attributes": True}


class RolePermissionUpdate(BaseModel):
    permission_ids: list[int]
