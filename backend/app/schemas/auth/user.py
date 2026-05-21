from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RoleMini(BaseModel):
    id: int
    role_name: str

    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    employee_id: str | None = None
    email: EmailStr | None = None
    full_name: str 
    department_id: int | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    employee_id: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None
    department_id: int | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: int
    profile_picture_url: str | None = None
    roles: list[RoleMini] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }


class UserListResponse(BaseModel):
    data: list[UserResponse]
    page: int
    page_size: int
    total: int


class UserRoleUpdate(BaseModel):
    role_ids: list[int]
