from datetime import datetime
from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: int
    user_agent: str | None = None
    ip_address: str | None = None
    expires_at: datetime
    revoked: bool
    revoked_at: datetime | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }