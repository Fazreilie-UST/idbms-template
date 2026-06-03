from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LogReportBase(BaseModel):
    title: str
    description: str
    page: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    severity: str
    status: str = "Open"
    screenshot_url: Optional[str] = None

class LogReportCreate(LogReportBase):
    pass

class LogReportUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    developer_notes: Optional[str] = None
    screenshot_url: Optional[str] = None

class LogReportOut(LogReportBase):
    id: int
    status: str
    submitted_by: int
    assigned_to: Optional[int]
    developer_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
