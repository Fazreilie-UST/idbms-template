from datetime import datetime, timedelta, timezone

from app.api.v1.endpoints import permissions
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session, joinedload

from app.db.deps import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_secure_token,
    hash_token,
)
from app.core.csrf import generate_csrf_token
from app.core.logging import security_logger, audit_logger
from app.core.rate_limit import limiter
from app.core.config import settings
from app.models.auth.user import User
from app.models.auth.role import Role
from app.models.auth.refresh_token import RefreshToken
from app.models.auth.password_reset_token import PasswordResetToken
from app.schemas.auth.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.schemas.auth.user import UserResponse
from app.schemas.auth.session import SessionResponse
from app.services.rbac_service import RBACService
from app.services.email_service import EmailService


router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_user_locked(user: User) -> bool:
    return bool(user.locked_until and user.locked_until > utc_now())


def register_failed_login(db: Session, user: User) -> None:
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = utc_now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)

    db.commit()


def reset_failed_login(db: Session, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


def build_token_payload(user: User) -> dict:
    roles = list(RBACService.get_user_roles(user))
    permissions = list(RBACService.get_user_permissions(user))

    return {
        "email": user.email,
        "roles": roles,
        "permissions": permissions,
        "token_version": user.token_version,
    }


def create_refresh_token_record(
    user_id: int,
    refresh_token: str,
    request: Request,
) -> RefreshToken:
    return RefreshToken(
        user_id=user_id,
        token_hash=hash_token(refresh_token),
        expires_at=utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
    )


def set_access_cookie(response: Response, access_token: str):
    """Set the httpOnly access-token cookie. Path=/ so any API call sees it."""
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_access_cookie(response: Response):
    response.delete_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        path="/",
    )


def set_csrf_cookie(response: Response, csrf_value: str):
    """Companion CSRF cookie for the double-submit pattern. NOT httpOnly so the
    SPA can read it and echo it back via the X-CSRF-Token header."""
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_value,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_csrf_cookie(response: Response):
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path="/",
    )


def issue_session_cookies(response: Response, access_token: str, refresh_token: str):
    """Set all three session cookies in a single call."""
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)
    set_csrf_cookie(response, generate_csrf_token())


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.email == data.email)
        .first()
    )

    if not user:
        security_logger.warning(
            "Login failed: email=%s reason=user_not_found",
            data.email,
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if is_user_locked(user):
        security_logger.warning(
            "Login blocked: user_id=%s email=%s reason=account_locked locked_until=%s",
            user.id,
            user.email,
            user.locked_until,
        )
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked due to too many failed login attempts",
        )

    if not user.can_login:
        security_logger.warning(
            "Login failed: user_id=%s email=%s reason=cannot_login",
            user.id,
            user.email,
        )
        raise HTTPException(status_code=403, detail="User cannot login")

    if not user.password_hash:
        security_logger.warning(
            "Login failed: user_id=%s email=%s reason=missing_password_hash",
            user.id,
            user.email,
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        register_failed_login(db, user)

        security_logger.warning(
            "Login failed: user_id=%s email=%s reason=invalid_password attempts=%s",
            user.id,
            user.email,
            user.failed_login_attempts,
        )

        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        security_logger.warning(
            "Login failed: user_id=%s email=%s reason=inactive_user",
            user.id,
            user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    access_token = create_access_token(
        subject=str(user.id),
        data=build_token_payload(user),
    )

    refresh_token = create_refresh_token(subject=str(user.id))

    refresh_token_record = create_refresh_token_record(
        user_id=user.id,
        refresh_token=refresh_token,
        request=request,
    )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_ = utc_now()

    db.add(refresh_token_record)
    db.commit()

    security_logger.info(
        "Login success: user_id=%s email=%s",
        user.id,
        user.email,
    )

    issue_session_cookies(response, access_token, refresh_token)

    roles = list(RBACService.get_user_roles(user))

    return {
        "token_type": "bearer",
        "access_token": access_token,
        "user" : {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "roles": roles,
            "profile_picture_url": user.profile_picture_url,
        },
    }


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_REFRESH)
def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)

    if not raw_refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    try:
        payload = decode_refresh_token(raw_refresh_token)
    except Exception:
        security_logger.warning("Refresh failed: invalid refresh token")
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")

    if not user_id:
        security_logger.warning("Refresh failed: missing token subject")
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    token_hash = hash_token(raw_refresh_token)

    stored_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == int(user_id),
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
        )
        .first()
    )

    if not stored_token:
        security_logger.warning(
            "Refresh failed: user_id=%s reason=token_not_found_or_revoked",
            user_id,
        )
        raise HTTPException(status_code=401, detail="Refresh token not found")

    if stored_token.expires_at < utc_now():
        stored_token.revoked = True
        stored_token.revoked_at = utc_now()
        db.commit()

        security_logger.warning(
            "Refresh failed: user_id=%s refresh_token_id=%s reason=expired",
            user_id,
            stored_token.id,
        )
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == int(user_id))
        .first()
    )

    if not user:
        security_logger.warning(
            "Refresh failed: user_id=%s reason=user_not_found",
            user_id,
        )
        raise HTTPException(status_code=401, detail="Invalid user")

    if not user.is_active or not user.can_login:
        security_logger.warning(
            "Refresh failed: user_id=%s reason=inactive_or_cannot_login",
            user.id,
        )
        raise HTTPException(status_code=401, detail="Invalid user")

    stored_token.revoked = True
    stored_token.revoked_at = utc_now()

    new_access_token = create_access_token(
        subject=str(user.id),
        data=build_token_payload(user),
    )

    new_refresh_token = create_refresh_token(subject=str(user.id))

    db.add(
        create_refresh_token_record(
            user_id=user.id,
            refresh_token=new_refresh_token,
            request=request,
        )
    )

    db.commit()

    security_logger.info(
        "Refresh token rotated: user_id=%s old_refresh_token_id=%s",
        user.id,
        stored_token.id,
    )

    issue_session_cookies(response, new_access_token, new_refresh_token)

    return {
        "token_type": "bearer",
        "access_token": new_access_token,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)

    if raw_refresh_token:
        token_hash = hash_token(raw_refresh_token)

        stored_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

        if stored_token and not stored_token.revoked:
            stored_token.revoked = True
            stored_token.revoked_at = utc_now()
            db.commit()

            security_logger.info(
                "Logout success: user_id=%s refresh_token_id=%s",
                stored_token.user_id,
                stored_token.id,
            )

    clear_refresh_cookie(response)
    clear_access_cookie(response)
    clear_csrf_cookie(response)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
@limiter.limit(settings.RATE_LIMIT_PASSWORD_RESET)
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    generic_response = {
        "message": "If the email exists, a reset link has been sent."
    }

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        security_logger.warning(
            "Password reset requested for unknown email=%s",
            data.email,
        )
        return generic_response

    if not user.can_login:
        security_logger.warning(
            "Password reset blocked: user_id=%s reason=cannot_login",
            user.id,
        )
        return generic_response

    raw_token = generate_secure_token()

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now()
        + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        used=False,
    )

    db.add(reset_token)
    db.commit()

    reset_link = f"{settings.PASSWORD_RESET_FRONTEND_URL}?token={raw_token}"

    try:
        EmailService.send_password_reset_email(
            to_email=user.email,
            reset_link=reset_link,
        )
    except Exception:
        security_logger.exception(
            "Password reset email failed: user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to send password reset email",
        )

    security_logger.info(
        "Password reset email sent: user_id=%s",
        user.id,
    )

    return generic_response


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_token(data.token)

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
        )
        .first()
    )

    if not reset_token:
        security_logger.warning("Password reset failed: invalid token")
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if reset_token.expires_at < utc_now():
        security_logger.warning(
            "Password reset failed: reset_token_id=%s reason=expired",
            reset_token.id,
        )
        raise HTTPException(status_code=400, detail="Reset token expired")

    user = db.query(User).filter(User.id == reset_token.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.email or not user.can_login:
        security_logger.warning(
            "Password reset failed: user_id=%s reason=user_cannot_login",
            user.id,
        )
        raise HTTPException(status_code=400, detail="User cannot reset password")

    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    user.is_active = True
    user.can_login = True
    reset_token.used = True

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update(
        {
            "revoked": True,
            "revoked_at": utc_now(),
        }
    )

    db.commit()

    audit_logger.info(
        "Password reset completed: user_id=%s",
        user.id,
    )

    return {"message": "Password reset successfully"}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()

    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Password cannot be changed")

    if not verify_password(data.current_password, user.password_hash):
        security_logger.warning(
            "Change password failed: user_id=%s reason=wrong_current_password",
            current_user.id,
        )
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(data.new_password)
    user.token_version += 1

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update(
        {
            "revoked": True,
            "revoked_at": utc_now(),
        }
    )

    db.commit()

    audit_logger.info(
        "Password changed: user_id=%s",
        user.id,
    )

    return {"message": "Password changed successfully. Please login again."}


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > utc_now(),
        )
        .order_by(RefreshToken.created_at.desc())
        .all()
    )


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.id == session_id,
            RefreshToken.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.revoked:
        session.revoked = True
        session.revoked_at = utc_now()

        db.commit()

    audit_logger.info(
        "Session revoked: user_id=%s session_id=%s",
        current_user.id,
        session_id,
    )

    return {"message": "Session revoked successfully"}


@router.post("/logout-all")
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
        )
        .update(
            {
                "revoked": True,
                "revoked_at": utc_now(),
            }
        )
    )

    db.commit()

    audit_logger.info(
        "Logout all sessions: user_id=%s sessions_revoked=%s",
        current_user.id,
        updated,
    )

    return {"message": "All sessions logged out successfully"}