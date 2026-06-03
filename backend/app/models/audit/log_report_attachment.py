from app.models.base import Base, Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class LogReportAttachment(Base):
    __tablename__ = "log_report_attachments"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("log_reports.id"), nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    report = relationship("LogReport", backref="attachments")
