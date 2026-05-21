from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db.deps import get_db
from app.core.dependencies import require_permission
from app.models.auth.permission import Permission
from app.models.auth.user import User
from app.schemas.auth.permission import PermissionResponse


router = APIRouter()


@router.get("/", response_model=list[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role:read")),
):
    rows = (
        db.query(Permission)
        .options(joinedload(Permission.action_category))
        .order_by(Permission.action_category_id.asc(), Permission.code.asc())
        .all()
    )
    return [
        PermissionResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            description=p.description,
            action_category_id=p.action_category_id,
            action_category_name=p.action_category.name if p.action_category else None,
        )
        for p in rows
    ]