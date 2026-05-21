import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.deps import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user, require_permission
from app.core.security import hash_password
from app.core.logging import audit_logger
from app.models.auth.user import User
from app.models.auth.role import Role
from app.models.auth.user_role import UserRole
from app.schemas.auth.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserRoleUpdate,
)


router = APIRouter()


_ALLOWED_AVATAR_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _profile_picture_storage_dir() -> Path:
    storage = Path(settings.PROFILE_PICTURE_DIR).expanduser().resolve()
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def _delete_profile_picture_file(url: str | None) -> None:
    """Best-effort removal of the on-disk file backing ``url``. Silent on
    failure so a stale DB pointer never blocks a new upload."""
    if not url:
        return
    name = url.rsplit("/", 1)[-1]
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        return
    try:
        (_profile_picture_storage_dir() / name).unlink(missing_ok=True)
    except OSError:
        pass


def _normalize_full_name(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip()


@router.post(
    "/",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:create"))],
)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    existing_email = db.query(User).filter(User.email == data.email).first()

    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")

    if data.employee_id:
        existing_employee = (
            db.query(User)
            .filter(User.employee_id == data.employee_id)
            .first()
        )

        if existing_employee:
            raise HTTPException(status_code=409, detail="Employee ID already exists")

    normalized_full_name = _normalize_full_name(data.full_name)

    if normalized_full_name:
        existing_name = (
            db.query(User)
            .filter(func.lower(User.full_name) == normalized_full_name.lower())
            .first()
        )

        if existing_name:
            raise HTTPException(status_code=409, detail="Full name already exists")

    user = User(
        employee_id=data.employee_id,
        email=data.email,
        full_name=normalized_full_name,
        department_id=data.department_id,
        password_hash=hash_password(data.password),
        is_active=data.is_active,
        can_login=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get(
    "/",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission("user:read"))],
)
def list_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    page: int | None = None,
    page_size: int | None = None,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
):
    q = db.query(User).options(joinedload(User.roles))

    if search:
        like = f"%{search.strip()}%"
        q = q.filter(
            (User.full_name.ilike(like))
            | (User.email.ilike(like))
            | (User.employee_id.ilike(like))
        )

    if role:
        q = (
            q.join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .filter(Role.role_name == role)
        )

    if is_active is not None:
        q = q.filter(User.is_active == is_active)

    # Sorting
    sort_map = {
        "id": User.id,
        "employee_id": User.employee_id,
        "full_name": User.full_name,
        "email": User.email,
        "department_id": User.department_id,
        "is_active": User.is_active,
        "created_at": User.created_at,
        "last_login": User.last_login_,
    }
    sort_col = sort_map.get((sort_by or "full_name").lower(), User.full_name)
    desc = (sort_order or "asc").lower() == "desc"
    order_clause = sort_col.desc() if desc else sort_col.asc()

    # Pagination: prefer page/page_size; fall back to skip/limit for callers
    # that still use the legacy contract.
    if page is not None or page_size is not None:
        p = max(1, page or 1)
        ps = max(1, min(page_size or 50, 200))
        offset = (p - 1) * ps
        ps_value = ps
    else:
        offset = max(0, skip)
        ps_value = max(1, min(limit, 500))
        p = (offset // ps_value) + 1

    total = q.distinct().count()
    users = (
        q.order_by(order_clause, User.id.asc())
        .offset(offset)
        .limit(ps_value)
        .all()
    )

    return UserListResponse(
        data=users,
        page=p,
        page_size=ps_value,
        total=total,
    )


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
def upload_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload (or replace) the current user's profile picture.

    Accepts a single image file (jpeg/png/webp/gif) up to
    ``settings.PROFILE_PICTURE_MAX_BYTES``. The previous file (if any) is
    removed from disk so old avatars don't accumulate.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported image type. Allowed: "
                f"{sorted(_ALLOWED_AVATAR_TYPES.keys())}"
            ),
        )

    suffix = _ALLOWED_AVATAR_TYPES[content_type]
    storage_dir = _profile_picture_storage_dir()
    stored_name = f"user_{current_user.id}_{secrets.token_hex(8)}{suffix}"
    target_path = storage_dir / stored_name

    max_bytes = settings.PROFILE_PICTURE_MAX_BYTES
    written = 0
    try:
        with target_path.open("wb") as out:
            while True:
                chunk = file.file.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Image exceeds max size of {max_bytes} bytes",
                    )
                out.write(chunk)
    finally:
        file.file.close()

    if written == 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty file")

    previous_url = current_user.profile_picture_url
    new_url = f"{settings.PROFILE_PICTURE_URL_PREFIX}/{stored_name}"
    current_user.profile_picture_url = new_url
    db.commit()
    db.refresh(current_user)

    if previous_url and previous_url != new_url:
        _delete_profile_picture_file(previous_url)

    audit_logger.info(
        "Profile picture uploaded: user_id=%s bytes=%s",
        current_user.id,
        written,
    )

    return current_user


@router.delete("/me/avatar", response_model=UserResponse)
def delete_my_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove the current user's profile picture (file + DB pointer)."""
    previous_url = current_user.profile_picture_url
    if previous_url:
        _delete_profile_picture_file(previous_url)
        current_user.profile_picture_url = None
        db.commit()
        db.refresh(current_user)
        audit_logger.info(
            "Profile picture removed: user_id=%s",
            current_user.id,
        )
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:read"))],
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("user:update")),):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)

    if "email" in update_data:
        existing_email = (
            db.query(User)
            .filter(User.email == update_data["email"], User.id != user_id)
            .first()
        )

        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")

    if "employee_id" in update_data and update_data["employee_id"]:
        existing_employee = (
            db.query(User)
            .filter(
                User.employee_id == update_data["employee_id"],
                User.id != user_id,
            )
            .first()
        )

        if existing_employee:
            raise HTTPException(status_code=409, detail="Employee ID already exists")

    if "full_name" in update_data:
        normalized_full_name = _normalize_full_name(update_data["full_name"])
        update_data["full_name"] = normalized_full_name

        if normalized_full_name:
            existing_name = (
                db.query(User)
                .filter(
                    func.lower(User.full_name) == normalized_full_name.lower(),
                    User.id != user_id,
                )
                .first()
            )

            if existing_name:
                raise HTTPException(status_code=409, detail="Full name already exists")

    for field, value in update_data.items():
        setattr(user, field, value)

    audit_logger.info(
        "User updated: target_user_id=%s updated_by=%s fields=%s",
        user_id,
        current_user.id,
        list(update_data.keys()),
    )

    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/{user_id}/roles",
)
def replace_user_roles(
    user_id: int,
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:update")),
):
    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    roles = db.query(Role).filter(Role.id.in_(data.role_ids)).all()

    if len(roles) != len(set(data.role_ids)):
        raise HTTPException(status_code=400, detail="One or more roles not found")

    db.query(UserRole).filter(UserRole.user_id == user.id).delete()

    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    user.token_version += 1
    
    audit_logger.info(
        "User roles updated: target_user_id=%s updated_by=%s role_ids=%s",
        user_id,
        current_user.id,
        data.role_ids,
    )

    db.commit()

    return {"message": "User roles updated successfully"}


@router.patch(
    "/{user_id}/activate",
    response_model=UserResponse,
)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update")),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.token_version += 1

    audit_logger.info(
        "User activated: target_user_id=%s updated_by=%s",
        user_id,
        current_user.id,
    )

    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserResponse,
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update")),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.token_version += 1

    audit_logger.info(
        "User deactivated: target_user_id=%s updated_by=%s",
        user_id,
        current_user.id,
    )

    db.commit()
    db.refresh(user)

    return user




# =========================================================================
# User Merge (deduplication)
# =========================================================================

class UserMergeResponse(BaseModel):
    primary_id: int
    duplicate_id: int
    transferred: dict[str, int] = {}
    deleted_conflicts: dict[str, int] = {}


# (table_name, fk_column, conflict_uniques)
# conflict_uniques: list of OTHER columns (besides the user FK) that, together
# with the user FK, form a unique constraint we must not violate when
# repointing duplicate's rows to primary.
_USER_FK_TABLES: list[tuple[str, str, list[str]]] = [
    # auth
    ("user_roles", "user_id", ["role_id"]),
    ("refresh_tokens", "user_id", []),
    ("password_reset_tokens", "user_id", []),
    # order
    ("user_build_requests", "requestor_id", ["build_request_id"]),
    ("build_requests", "requestor_id", []),
    ("shippings", "recipient_user_id", []),
    # build_plan_shippings has unique (build_plan_id, recipient_user_id,
    # requestor_user_id); duplicates on either side are dropped in favour
    # of the primary user's existing rows.
    ("build_plan_shippings", "recipient_user_id", ["build_plan_id", "requestor_user_id"]),
    ("build_plan_shippings", "requestor_user_id", ["build_plan_id", "recipient_user_id"]),
    # build
    ("build_plan_access", "user_id", ["family_form_factor_id"]),
    ("build_plan_import_files", "uploaded_by_id", []),
    # storage / stock / audit
    ("stored_files", "uploaded_by_id", []),
    ("import_jobs", "imported_by_id", []),
    ("audit_logs", "user_id", []),
]


@router.post(
    "/{primary_id}/merge/{duplicate_id}",
    response_model=UserMergeResponse,
)
def merge_users(
    primary_id: int,
    duplicate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update")),
):
    """Merge ``duplicate_id`` into ``primary_id``.

    All foreign-key references to the duplicate user across the system are
    repointed to the primary user. Rows that would violate uniqueness
    constraints (e.g. user already has a given role, already in a recipient
    group, etc.) are deleted from the duplicate side instead of being
    repointed. The duplicate user row is then deleted.

    The primary user's ``token_version`` is bumped so any in-flight JWTs
    that may have been minted with stale role/permission data are
    invalidated.
    """
    if primary_id == duplicate_id:
        raise HTTPException(status_code=400, detail="Cannot merge a user into itself")
    if duplicate_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot merge yourself away")

    primary = db.query(User).filter(User.id == primary_id).first()
    duplicate = db.query(User).filter(User.id == duplicate_id).first()
    if not primary or not duplicate:
        raise HTTPException(status_code=404, detail="One or both users not found")

    transferred: dict[str, int] = {}
    deleted: dict[str, int] = {}

    try:
        for table, fk_col, uniques in _USER_FK_TABLES:
            if uniques:
                # Drop duplicate's rows that would collide on (fk_col, *uniques)
                cols = ", ".join(uniques)
                sql = f"""
                    DELETE FROM {table}
                    WHERE {fk_col} = :dup
                      AND ({cols}) IN (
                        SELECT {cols} FROM {table} WHERE {fk_col} = :pri
                      )
                """
                r = db.execute(text(sql), {"dup": duplicate_id, "pri": primary_id})
                deleted[table] = (deleted.get(table, 0) + (r.rowcount or 0))

            if table == "":
                # Reserved for special-cased tables.
                continue

            r = db.execute(
                text(f"UPDATE {table} SET {fk_col} = :pri WHERE {fk_col} = :dup"),
                {"dup": duplicate_id, "pri": primary_id},
            )
            transferred[table] = (transferred.get(table, 0) + (r.rowcount or 0))

        # Bump token version so stale tokens for either side get rejected
        primary.token_version = (primary.token_version or 0) + 1

        # Finally remove the duplicate user
        db.delete(duplicate)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Merge failed: {e.orig}") from e

    audit_logger.info(
        "Users merged: primary_id=%s duplicate_id=%s by=%s",
        primary_id,
        duplicate_id,
        current_user.id,
    )

    return UserMergeResponse(
        primary_id=primary_id,
        duplicate_id=duplicate_id,
        transferred=transferred,
        deleted_conflicts=deleted,
    )
