from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LogReportAttachmentOut(BaseModel):
    id: int
    report_id: int
    file_url: str
    uploaded_at: datetime

    class Config:
        orm_mode = True
