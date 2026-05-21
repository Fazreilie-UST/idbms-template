from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.deps import get_db
from app.core.dependencies import require_permission
from app.core.logging import audit_logger
from app.models.auth.role import Role
from app.models.auth.permission import Permission
from app.models.auth.role_permission import RolePermission
from app.models.auth.user import User
from app.schemas.auth.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RolePermissionUpdate,
)


router = APIRouter()


@router.get("/", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role:read")),
):
    roles = (
        db.query(Role)
        .options(joinedload(Role.permissions))
        .order_by(Role.id.asc())
        .all()
    )
    return roles


@router.post("/", response_model=RoleResponse)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:create")),
):
    if db.query(Role).filter(Role.role_name == data.role_name).first():
        raise HTTPException(status_code=409, detail="Role already exists")

    role = Role(role_name=data.role_name, description=data.description)
    db.add(role)
    db.commit()
    db.refresh(role)

    audit_logger.info(
        "Role created: role_id=%s name=%s by=%s",
        role.id, role.role_name, current_user.id,
    )
    return role


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role:read")),
):
    role = (
        db.query(Role)
        .options(joinedload(Role.permissions))
        .filter(Role.id == role_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:update")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)

    audit_logger.info(
        "Role updated: role_id=%s by=%s fields=%s",
        role_id, current_user.id, list(update_data.keys()),
    )
    return role


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:delete")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    db.delete(role)
    db.commit()

    audit_logger.info(
        "Role deleted: role_id=%s by=%s", role_id, current_user.id,
    )
    return {"message": "Role deleted"}


@router.patch("/{role_id}/permissions")
def replace_role_permissions(
    role_id: int,
    data: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:update")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    perms = db.query(Permission).filter(Permission.id.in_(data.permission_ids)).all()
    if len(perms) != len(set(data.permission_ids)):
        raise HTTPException(status_code=400, detail="One or more permissions not found")

    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    for p in perms:
        db.add(RolePermission(role_id=role.id, permission_id=p.id))

    for u in role.users:
        u.token_version += 1

    db.commit()

    audit_logger.info(
        "Role permissions updated: role_id=%s by=%s permission_ids=%s",
        role_id, current_user.id, data.permission_ids,
    )
    return {"message": "Role permissions updated"}