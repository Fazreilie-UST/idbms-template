from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.db.deps import get_db
from app.models.auth.user import User
from app.models.auth.role import Role
from app.core.config import settings
from app.core.security import decode_access_token
from app.services.rbac_service import RBACService
from app.core.logging import security_logger, rbac_logger


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Prefer the httpOnly cookie set by the auth flow; fall back to a
    # `Authorization: Bearer <jwt>` header for non-browser clients (CLI tools,
    # service-to-service calls). The cookie path is XSS-resistant; the bearer
    # path is left intact for backwards compatibility but exempt from CSRF.
    raw_token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if not raw_token and credentials is not None:
        raw_token = credentials.credentials

    if not raw_token:
        security_logger.warning("Authentication failed: missing access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(raw_token)
    except Exception:
        security_logger.warning("Authentication failed: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    if not user_id:
        security_logger.warning("Authentication failed: missing token subject")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == int(user_id))
        .first()
    )

    if not user:
        security_logger.warning("Authentication failed: user_id=%s not found", user_id)
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        security_logger.warning("Inactive user attempted access: user_id=%s", user.id)
        raise HTTPException(status_code=403, detail="User is inactive")
    
    token_version = payload.get("token_version")

    if token_version is None or token_version != user.token_version:
        security_logger.warning(
            "Authentication failed: stale token user_id=%s",
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is no longer valid",
        )

    user.token_permissions = set(payload.get("permissions", []))
    user.token_roles = set(payload.get("roles", []))

    return user


def require_permission(permission_code: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        token_permissions = getattr(current_user, "token_permissions", set())

        allowed = RBACService.has_permission(
            user_permissions=token_permissions,
            required_permission=permission_code,
        )

        if not allowed:
            rbac_logger.warning(
                "Permission denied: user_id=%s required=%s user_permissions=%s",
                current_user.id,
                permission_code,
                sorted(token_permissions),
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permission",
            )

        return current_user

    return checker


def require_any_permission(permission_codes: list[str]):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        token_permissions = getattr(current_user, "token_permissions", set())

        allowed = RBACService.has_any_permission(
            user_permissions=token_permissions,
            required_permissions=permission_codes,
        )

        if not allowed:
            rbac_logger.warning(
                "Permission denied: user_id=%s required_any=%s",
                current_user.id,
                permission_codes,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permission",
            )

        return current_user

    return checker


def require_all_permissions(permission_codes: list[str]):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        token_permissions = getattr(current_user, "token_permissions", set())

        allowed = RBACService.has_all_permissions(
            user_permissions=token_permissions,
            required_permissions=permission_codes,
        )

        if not allowed:
            rbac_logger.warning(
                "Permission denied: user_id=%s required_all=%s",
                current_user.id,
                permission_codes,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permission",
            )

        return current_user

    return checker