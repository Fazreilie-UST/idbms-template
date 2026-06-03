
from sqlalchemy.orm import Session
from app.models.audit.log_report import LogReport
from app.schemas.log_report import LogReportCreate, LogReportUpdate
from app.services.audit_service import AuditService
from app.models.audit.audit_log import AuditModule, AuditAction
from typing import List, Optional

def create_log_report(db: Session, report: LogReportCreate, user_id: int) -> LogReport:
    db_report = LogReport(**report.dict(), submitted_by=user_id)
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def get_log_report(db: Session, report_id: int) -> Optional[LogReport]:
    return db.query(LogReport).filter(LogReport.id == report_id).first()

def get_my_log_reports(db: Session, user_id: int) -> List[LogReport]:
    return db.query(LogReport).filter(LogReport.submitted_by == user_id).all()

def get_all_log_reports(db: Session) -> List[LogReport]:
    return db.query(LogReport).all()

def update_log_report(db: Session, report_id: int, update: LogReportUpdate) -> Optional[LogReport]:
    db_report = db.query(LogReport).filter(LogReport.id == report_id).first()
    if not db_report:
        print(f"[DEBUG] update_log_report: Report {report_id} not found.")
        return None
    update_fields = update.dict(exclude_unset=True)
    print(f"[DEBUG] update_log_report: Updating fields {update_fields}")
    for field, value in update_fields.items():
        setattr(db_report, field, value)
    db.commit()
    db.refresh(db_report)
    print(f"[DEBUG] update_log_report: After update, screenshot_url={db_report.screenshot_url}")
    return db_report
