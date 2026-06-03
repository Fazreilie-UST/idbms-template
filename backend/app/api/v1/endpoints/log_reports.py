from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
import os
from sqlalchemy.orm import Session
from typing import List
from app.schemas.log_report import LogReportCreate, LogReportOut, LogReportUpdate
from app.schemas.log_report_attachment import LogReportAttachmentOut
from app.services.log_report_service import (
    create_log_report, get_log_report, get_my_log_reports, get_all_log_reports, update_log_report
)
from app.db.deps import get_db
from app.core.dependencies import get_current_user
from app.models.auth.user import User

router = APIRouter()

@router.post("/log-reports", response_model=LogReportOut)
def submit_log_report(
    report: LogReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_log_report(db, report, current_user.id)

@router.get("/log-reports/my", response_model=List[LogReportOut])
def list_my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_log_reports(db, current_user.id)

@router.get("/log-reports", response_model=List[LogReportOut])
def list_all_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # RBAC: Only admin/dev roles can access all reports
    if not any(role.role_name in ("Admin", "Developer") for role in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized")
    return get_all_log_reports(db)

@router.get("/log-reports/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.log_report_service import get_log_report
    from app.models.audit.log_report_attachment import LogReportAttachment
    report = get_log_report(db, report_id)
    if not report:
        return JSONResponse(status_code=404, content={"detail": "Report not found"})
    if report.submitted_by != current_user.id and not any(role.role_name in ("Admin", "Developer") for role in current_user.roles):
        return JSONResponse(status_code=403, content={"detail": "Not authorized"})
    # Get all attachments for this report
    attachments = db.query(LogReportAttachment).filter(LogReportAttachment.report_id == report_id).all()
    # Return report fields plus attachments
    report_dict = report.__dict__.copy()
    report_dict["attachments"] = [
        {"id": a.id, "file_url": a.file_url, "uploaded_at": a.uploaded_at.isoformat()} for a in attachments
    ]
    return report_dict
@router.post("/log-reports/{report_id}/attachments")
async def upload_attachment(
    report_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    from app.services.log_report_service import get_log_report
    from app.models.audit.log_report_attachment import LogReportAttachment
    report = get_log_report(db, report_id)
    if not report:
        return JSONResponse(status_code=404, content={"detail": "Report not found"})
    if report.submitted_by != current_user.id and not any(role.role_name in ("Admin", "Developer") for role in current_user.roles):
        return JSONResponse(status_code=403, content={"detail": "Not authorized"})
    # File size limit (5MB)
    MAX_SIZE = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        return JSONResponse(status_code=413, content={"detail": "File too large (max 5MB)"})
    # File type validation
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        return JSONResponse(status_code=415, content={"detail": "Unsupported file type. Allowed: jpg, png, pdf."})
    # Save file with unique name
    import uuid
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../'))
    upload_dir = os.path.join(project_root, "db", "bug-report-attachment")
    os.makedirs(upload_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    unique_id = uuid.uuid4().hex[:8]
    save_name = f"bug_{report_id}_{unique_id}{file_ext}"
    save_path = os.path.join(upload_dir, save_name)
    with open(save_path, "wb") as f:
        f.write(content)
    base_url = str(request.base_url).rstrip("/")
    url_path = f"/db/bug-report-attachment/{save_name}"
    file_url = base_url + url_path
    # Insert attachment record
    attachment = LogReportAttachment(report_id=report_id, file_url=file_url)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {"filename": file.filename, "url": file_url, "attachment_id": attachment.id}
