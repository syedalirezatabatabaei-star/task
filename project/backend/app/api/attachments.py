import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.task import Task
from app.models.attachment import Attachment
from app.api.deps import get_current_user, require_permission, get_client_ip
from app.services.audit_service import log_action
from app.core import permissions as P

router = APIRouter(tags=["Attachments"])


@router.get("/tasks/{task_id}/attachments", summary="پیوست‌های وظیفه")
def list_attachments(
    task_id: int,
    current_user: User = Depends(require_permission(P.ATTACHMENTS_VIEW)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    _check_task_access(task, current_user)

    attachments = db.query(Attachment).filter(Attachment.task_id == task_id).all()
    return {"success": True, "data": [_att_dict(a) for a in attachments]}


@router.post("/tasks/{task_id}/attachments", status_code=status.HTTP_201_CREATED, summary="آپلود پیوست")
async def upload_attachment(
    task_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(P.ATTACHMENTS_UPLOAD)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    _check_task_access(task, current_user)

    # Validate MIME type (client-provided MIME alone is not trustworthy).
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail={"success": False, "message": "نوع فایل مجاز نیست", "code": "INVALID_MIME"},
        )

    # Read at most the configured limit plus one byte to avoid unbounded memory use.
    content = await file.read(settings.MAX_UPLOAD_SIZE + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"success": False, "message": "حجم فایل بیش از حد مجاز است", "code": "FILE_TOO_LARGE"},
        )

    # Sanitize and store with UUID name
    original_name = os.path.basename(file.filename or "file")
    ext = os.path.splitext(original_name)[1].lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(task_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_name)

    with open(file_path, "wb") as f:
        f.write(content)

    attachment = Attachment(
        task_id=task_id,
        uploaded_by=current_user.id,
        original_filename=original_name,
        stored_filename=stored_name,
        file_path=file_path,
        mime_type=file.content_type,
        file_size=len(content),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    log_action(
        db=db, user_id=current_user.id, action="ATTACHMENT_UPLOADED",
        entity_type="task", entity_id=task_id,
        description=f"فایل '{original_name}' برای وظیفه آپلود شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _att_dict(attachment)}


@router.get("/attachments/{attachment_id}/download", summary="دریافت پیوست")
def download_attachment(
    attachment_id: int,
    current_user: User = Depends(require_permission(P.ATTACHMENTS_VIEW)),
    db: Session = Depends(get_db),
):
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail={"success": False, "message": "پیوست یافت نشد"})
    task = _get_task_or_404(att.task_id, db)
    _check_task_access(task, current_user)
    if not os.path.isfile(att.file_path):
        raise HTTPException(status_code=404, detail={"success": False, "message": "فایل روی سرور موجود نیست"})
    return FileResponse(att.file_path, media_type="application/octet-stream", filename=att.original_filename, content_disposition_type="attachment")


@router.delete("/attachments/{attachment_id}", summary="حذف پیوست")
def delete_attachment(
    attachment_id: int,
    request: Request,
    current_user: User = Depends(require_permission(P.ATTACHMENTS_UPLOAD)),
    db: Session = Depends(get_db),
):
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail={"success": False, "message": "پیوست یافت نشد"})

    # Only uploader or admin can delete
    if att.uploaded_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail={"success": False, "message": "دسترسی ندارید"})

    file_path = att.file_path
    task_id = att.task_id
    original_filename = att.original_filename
    db.delete(att)
    db.commit()

    # Delete the physical file only after the database transaction succeeds.
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            # Metadata is already removed; an orphaned file can be cleaned up later.
            pass
    log_action(db=db, user_id=current_user.id, action="ATTACHMENT_DELETED", entity_type="task", entity_id=task_id, description=f"فایل '{original_filename}' حذف شد", ip_address=get_client_ip(request))
    return {"success": True, "message": "پیوست حذف شد"}


def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"success": False, "message": "وظیفه یافت نشد"})
    return task


def _check_task_access(task: Task, user: User):
    if user.role == UserRole.ADMIN:
        return
    if task.assigned_to != user.id:
        raise HTTPException(status_code=403, detail={"success": False, "message": "دسترسی ندارید"})


def _att_dict(a: Attachment) -> dict:
    return {
        "id": a.id,
        "task_id": a.task_id,
        "uploaded_by": a.uploaded_by,
        "original_filename": a.original_filename,
        "mime_type": a.mime_type,
        "file_size": a.file_size,
        "created_at": a.created_at.isoformat(),
        "download_url": f"/api/v1/attachments/{a.id}/download",
    }
