from sqlalchemy.orm import Session
from app.models.auth.user import User
from app.models.auth.role import Role
from app.models.auth.permission import Permission
from app.services.audit_service import AuditService
from app.models.audit.audit_log import AuditModule, AuditAction

def audit_user_role_assignment(db: Session, user: User, role: Role, actor_id: int):
    AuditService.record(
        db,
        module=AuditModule.user,
        action=AuditAction.assign,
        record_id=user.id,
        user_id=actor_id,
        old_value=None,
        new_value={"assigned_role": role.role_name},
    )

def audit_role_permission_assignment(db: Session, role: Role, permission: Permission, actor_id: int):
    AuditService.record(
        db,
        module=AuditModule.user,
        action=AuditAction.assign,
        record_id=role.id,
        user_id=actor_id,
        old_value=None,
        new_value={"assigned_permission": permission.code},
    )
