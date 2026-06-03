
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import List, Optional
from app.models.audit.audit_log import AuditLog
from app.db.deps import get_db
from app.core.dependencies import get_current_user
from app.models.auth.user import User

router = APIRouter()

from datetime import datetime

@router.get("/audit-logs", response_model=List[dict])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
):
    # Only admin/dev can access
    if not any(role.role_name in ("Admin", "Developer") for role in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized")
    q = db.query(AuditLog)
    if start_date:
        q = q.filter(AuditLog.created_at >= start_date)
    if end_date:
        q = q.filter(AuditLog.created_at <= end_date)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if module:
        q = q.filter(AuditLog.module == module)
    if ip_address:
        q = q.filter(AuditLog.ip_address == ip_address)
    logs = q.order_by(AuditLog.created_at.desc()).all()
    # Return only serializable fields
    def serialize(log):
        return {
            "id": log.id,
            "user_id": log.user_id,
            "module": str(log.module) if log.module else None,
            "action": str(log.action) if log.action else None,
            "record_id": log.record_id,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "created_at": log.created_at.isoformat() if isinstance(log.created_at, datetime) else str(log.created_at),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
        }
    return [serialize(log) for log in logs]


# New endpoint: Get unique filter values for dropdowns
@router.get("/audit-logs/filters", response_model=dict)
def get_audit_log_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only admin/dev can access
    if not any(role.role_name in ("Admin", "Developer") for role in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized")

    user_ids = [r[0] for r in db.query(distinct(AuditLog.user_id)).all() if r[0] is not None]
    actions = [r[0] for r in db.query(distinct(AuditLog.action)).all() if r[0] is not None]
    modules = [r[0] for r in db.query(distinct(AuditLog.module)).all() if r[0] is not None]
    ip_addresses = [r[0] for r in db.query(distinct(AuditLog.ip_address)).all() if r[0] is not None]

    return {
        "user_ids": user_ids,
        "actions": actions,
        "modules": modules,
        "ip_addresses": ip_addresses,
    }
