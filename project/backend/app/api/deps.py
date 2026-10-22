"""
FastAPI dependencies for authentication and authorization.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.models.permission import UserPermission, Permission

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT and return the current user. Raises 401 if invalid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "احراز هویت الزامی است", "code": "UNAUTHORIZED"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "توکن نامعتبر یا منقضی شده است", "code": "INVALID_TOKEN"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "توکن نامعتبر است", "code": "INVALID_TOKEN"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "کاربر یافت نشد", "code": "USER_NOT_FOUND"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "حساب کاربری غیرفعال است", "code": "ACCOUNT_DISABLED"},
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an ADMIN."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "دسترسی فقط برای مدیران", "code": "ADMIN_REQUIRED"},
        )
    return current_user


def get_user_permission_codes(user: User, db: Session) -> set[str]:
    """Return the set of permission codes for a user. Admins get everything."""
    if user.role == UserRole.ADMIN:
        # Admin has all permissions
        all_permissions = db.query(Permission).all()
        return {p.code for p in all_permissions}

    permissions = (
        db.query(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .filter(UserPermission.user_id == user.id)
        .all()
    )
    return {p.code for p in permissions}


def require_permission(permission_code: str):
    """Factory: returns a dependency that checks for a specific permission."""
    def _checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.role == UserRole.ADMIN:
            return current_user
        codes = get_user_permission_codes(current_user, db)
        if permission_code not in codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": "شما اجازه دسترسی به این بخش را ندارید.",
                    "code": "PERMISSION_DENIED",
                },
            )
        return current_user
    return _checker


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
