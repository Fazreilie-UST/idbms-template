from app.models.base import Base, Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship

class LogReport(Base):
    __tablename__ = "log_reports"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    page = Column(String, nullable=True)
    steps_to_reproduce = Column(Text, nullable=True)
    expected_behavior = Column(Text, nullable=True)
    actual_behavior = Column(Text, nullable=True)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Open")
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    screenshot_url = Column(String, nullable=True)
    developer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    submitter = relationship("User", foreign_keys=[submitted_by], backref="submitted_reports")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_reports")
