from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.permission import Permission, UserPermission
from app.schemas.permission import UserPermissionUpdate
from app.api.deps import get_current_user, require_admin, get_client_ip
from app.services.audit_service import log_action

router = APIRouter(tags=["Permissions"])


@router.get("/permissions", summary="لیست همه دسترسی‌ها")
def list_permissions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    permissions = db.query(Permission).order_by(Permission.code).all()
    return {
        "success": True,
        "data": [
            {"id": p.id, "code": p.code, "name": p.name, "description": p.description}
            for p in permissions
        ],
    }


@router.get("/users/{user_id}/permissions", summary="دسترسی‌های کاربر")
def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    if user.role == UserRole.ADMIN:
        # Admin has all permissions
        all_perms = db.query(Permission).all()
        return {
            "success": True,
            "data": {
                "user_id": user.id,
                "is_admin": True,
                "permissions": [p.code for p in all_perms],
            },
        }

    user_perms = (
        db.query(Permission)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .filter(UserPermission.user_id == user_id)
        .all()
    )
    return {
        "success": True,
        "data": {
            "user_id": user.id,
            "is_admin": False,
            "permissions": [p.code for p in user_perms],
        },
    }


@router.put("/users/{user_id}/permissions", summary="بروزرسانی کامل دسترسی‌های کاربر")
def update_user_permissions(
    user_id: int,
    body: UserPermissionUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)

    # Get permission records from codes
    permissions = db.query(Permission).filter(Permission.code.in_(body.permission_codes)).all()
    found_codes = {p.code for p in permissions}
    missing = set(body.permission_codes) - found_codes
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": f"دسترسی‌های نامعتبر: {missing}", "code": "INVALID_PERMISSIONS"},
        )

    # Delete existing permissions
    db.query(UserPermission).filter(UserPermission.user_id == user_id).delete()

    # Add new permissions
    for perm in permissions:
        up = UserPermission(user_id=user_id, permission_id=perm.id)
        db.add(up)

    db.commit()

    log_action(
        db=db, user_id=current_user.id, action="PERMISSION_CHANGED",
        entity_type="user", entity_id=user.id,
        description=f"دسترسی‌های کاربر {user.username} به‌روز شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "message": "دسترسی‌ها با موفقیت به‌روز شد"}


@router.post("/users/{user_id}/permissions/{permission_id}", summary="افزودن یک دسترسی")
def add_user_permission(
    user_id: int,
    permission_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _get_user_or_404(user_id, db)
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail={"success": False, "message": "دسترسی یافت نشد"})

    existing = db.query(UserPermission).filter(
        UserPermission.user_id == user_id,
        UserPermission.permission_id == permission_id,
    ).first()
    if not existing:
        up = UserPermission(user_id=user_id, permission_id=permission_id)
        db.add(up)
        db.commit()

    return {"success": True, "message": "دسترسی اضافه شد"}


@router.delete("/users/{user_id}/permissions/{permission_id}", summary="حذف یک دسترسی")
def remove_user_permission(
    user_id: int,
    permission_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    up = db.query(UserPermission).filter(
        UserPermission.user_id == user_id,
        UserPermission.permission_id == permission_id,
    ).first()
    if up:
        db.delete(up)
        db.commit()

    return {"success": True, "message": "دسترسی حذف شد"}


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": "کاربر یافت نشد", "code": "NOT_FOUND"},
        )
    return user
