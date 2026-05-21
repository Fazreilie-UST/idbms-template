from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    action_category_id: int | None = None
    action_category_name: str | None = None

    model_config = {"from_attributes": True}
