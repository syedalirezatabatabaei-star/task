from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.api.deps import get_current_user, get_client_ip
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, summary="ورود به سیستم")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user and return JWT access token."""
    user = db.query(User).filter(User.username == body.username).first()

    # Generic error to prevent username enumeration
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "نام کاربری یا رمز عبور اشتباه است",
                "code": "INVALID_CREDENTIALS",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "حساب کاربری شما غیرفعال است",
                "code": "ACCOUNT_DISABLED",
            },
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Use the request-scoped database session so audit events follow the same
    # database configuration as the request and remain isolated in tests.
    log_action(
        db=db,
        user_id=user.id,
        action="USER_LOGIN",
        entity_type="user",
        entity_id=user.id,
        description=f"ورود کاربر {user.username}",
        ip_address=get_client_ip(request),
    )
    db.commit()

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
    )


@router.get("/me", summary="اطلاعات کاربر جاری")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return current user profile and permission codes."""
    from app.api.deps import get_user_permission_codes
    permission_codes = get_user_permission_codes(current_user, db)

    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role.value,
            "full_name": current_user.full_name,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "is_active": current_user.is_active,
            "start_date": current_user.start_date.isoformat() if current_user.start_date else None,
            "end_date": current_user.end_date.isoformat() if current_user.end_date else None,
            "permissions": list(permission_codes),
        },
    }


@router.post("/logout", summary="خروج از سیستم")
def logout(current_user: User = Depends(get_current_user)):
    """Logout — client should discard the token."""
    return {"success": True, "message": "با موفقیت خارج شدید"}
