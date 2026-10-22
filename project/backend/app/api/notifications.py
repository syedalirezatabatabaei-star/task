from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_admin
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=10000)
    scope: Literal["public", "private"] = "public"
    recipient_user_id: int | None = None


def _item(row: Notification) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "message": row.message,
        "scope": row.scope,
        "is_read": row.is_read,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("", summary="اعلان‌های کاربر فعلی")
def list_notifications(
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    unread_count = query.filter(Notification.is_read.is_(False)).count()
    rows = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()
    return {"success": True, "data": {"items": [_item(row) for row in rows], "unread_count": unread_count}}


@router.patch("/{notification_id}/read", summary="خوانده‌شدن اعلان")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail={"message": "اعلان یافت نشد"})
    row.is_read = True
    db.commit()
    return {"success": True, "data": _item(row)}


@router.patch("/read-all", summary="خوانده‌شدن همه اعلان‌ها")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"success": True, "message": "همه اعلان‌ها خوانده شدند"}


@router.post("/announcements", status_code=status.HTTP_201_CREATED, summary="انتشار اعلان عمومی یا خصوصی")
def create_announcement(
    body: AnnouncementCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    title = body.title.strip()
    message = body.message.strip()
    if not title or not message:
        raise HTTPException(status_code=422, detail={"message": "عنوان و متن اعلان الزامی است"})

    if body.scope == "private":
        if not body.recipient_user_id:
            raise HTTPException(status_code=422, detail={"message": "برای اعلان خصوصی، انتخاب کاربر الزامی است"})
        recipients = db.query(User).filter(
            User.id == body.recipient_user_id, User.is_active.is_(True)
        ).all()
        if not recipients:
            raise HTTPException(status_code=404, detail={"message": "کاربر فعال یافت نشد"})
    else:
        recipients = db.query(User).filter(User.is_active.is_(True)).all()
        if not recipients:
            raise HTTPException(status_code=409, detail={"message": "کاربر فعالی برای دریافت اعلان وجود ندارد"})

    rows = [
        Notification(
            user_id=recipient.id,
            created_by=current_user.id,
            title=title,
            message=message,
            scope=body.scope,
            is_read=False,
        )
        for recipient in recipients
    ]
    db.add_all(rows)
    db.commit()
    return {
        "success": True,
        "data": {"recipient_count": len(rows), "scope": body.scope},
        "message": "اعلان منتشر شد",
    }
