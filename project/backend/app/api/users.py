from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserPasswordReset, UserStatusUpdate, UserResponse, UserListItem
from app.schemas.common import PaginatedResponse, ResponseModel
from app.api.deps import get_current_user, require_permission, require_admin, get_client_ip
from app.services.audit_service import log_action
from app.core import permissions as P

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", summary="لیست کاربران")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_permission(P.USERS_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(User)

    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": u.id,
                    "username": u.username,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "full_name": u.full_name,
                    "email": u.email,
                    "role": u.role.value,
                    "is_active": u.is_active,
                    "start_date": u.start_date.isoformat() if u.start_date else None,
                    "end_date": u.end_date.isoformat() if u.end_date else None,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="ایجاد کاربر")
def create_user(
    body: UserCreate,
    request: Request,
    current_user: User = Depends(require_permission(P.USERS_CREATE)),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "message": "این نام کاربری قبلاً ثبت شده است", "code": "USERNAME_EXISTS"},
        )

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        start_date=body.start_date,
        end_date=body.end_date,
        description=body.description,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db=db, user_id=current_user.id, action="USER_CREATED",
        entity_type="user", entity_id=user.id,
        description=f"کاربر {user.username} ایجاد شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _user_dict(user)}


@router.get("/{user_id}", summary="جزئیات کاربر")
def get_user(
    user_id: int,
    current_user: User = Depends(require_permission(P.USERS_VIEW)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    return {"success": True, "data": _user_dict(user)}


@router.put("/{user_id}", summary="ویرایش کاربر")
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.USERS_EDIT)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    log_action(
        db=db, user_id=current_user.id, action="USER_UPDATED",
        entity_type="user", entity_id=user.id,
        description=f"کاربر {user.username} ویرایش شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _user_dict(user)}


@router.delete("/{user_id}", summary="حذف کاربر")
def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_permission(P.USERS_DELETE)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "نمی‌توانید حساب خود را حذف کنید", "code": "SELF_DELETE"},
        )
    # Prevent deleting the last admin
    if user.role == UserRole.ADMIN:
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN, User.is_active == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "حداقل یک مدیر باید وجود داشته باشد", "code": "LAST_ADMIN"},
            )

    log_action(
        db=db, user_id=current_user.id, action="USER_DELETED",
        entity_type="user", entity_id=user.id,
        description=f"کاربر {user.username} حذف شد",
        ip_address=get_client_ip(request),
    )

    db.delete(user)
    db.commit()
    return {"success": True, "message": "کاربر با موفقیت حذف شد"}


@router.patch("/{user_id}/status", summary="تغییر وضعیت کاربر")
def update_status(
    user_id: int,
    body: UserStatusUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.USERS_EDIT)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "نمی‌توانید وضعیت حساب خود را تغییر دهید", "code": "SELF_STATUS"},
        )

    user.is_active = body.is_active
    db.commit()

    log_action(
        db=db, user_id=current_user.id, action="USER_STATUS_CHANGED",
        entity_type="user", entity_id=user.id,
        description=f"وضعیت کاربر {user.username} به {'فعال' if body.is_active else 'غیرفعال'} تغییر یافت",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "message": "وضعیت کاربر تغییر کرد"}


@router.post("/{user_id}/reset-password", summary="بازنشانی رمز عبور")
def reset_password(
    user_id: int,
    body: UserPasswordReset,
    request: Request,
    current_user: User = Depends(require_permission(P.USERS_EDIT)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    user.password_hash = hash_password(body.new_password)
    db.commit()

    log_action(
        db=db, user_id=current_user.id, action="PASSWORD_RESET",
        entity_type="user", entity_id=user.id,
        description=f"رمز عبور کاربر {user.username} بازنشانی شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "message": "رمز عبور با موفقیت تغییر یافت"}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "کاربر یافت نشد", "code": "NOT_FOUND"},
        )
    return user


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.value,
        "is_active": user.is_active,
        "start_date": user.start_date.isoformat() if user.start_date else None,
        "end_date": user.end_date.isoformat() if user.end_date else None,
        "description": user.description,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
