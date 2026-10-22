from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.evaluation import Evaluation
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskProgressUpdate, TaskSubmit
from app.api.deps import get_current_user, require_permission, get_client_ip
from app.services.audit_service import log_action
from app.core import permissions as P

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Valid status transitions
VALID_TRANSITIONS = {
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS],
    TaskStatus.IN_PROGRESS: [TaskStatus.SUBMITTED],
    TaskStatus.SUBMITTED: [TaskStatus.APPROVED, TaskStatus.NEEDS_REVISION],
    TaskStatus.NEEDS_REVISION: [TaskStatus.IN_PROGRESS],
    TaskStatus.APPROVED: [TaskStatus.DONE],
    TaskStatus.DONE: [],
}


@router.get("", summary="لیست وظایف")
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    stage_id: Optional[int] = Query(None),
    assigned_to: Optional[int] = Query(None),
    task_status: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[TaskPriority] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(P.TASKS_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Task)

    # Non-admins only see their own assigned tasks
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Task.assigned_to == current_user.id)

    if project_id:
        query = query.filter(Task.project_id == project_id)
    if stage_id:
        query = query.filter(Task.stage_id == stage_id)
    if assigned_to and current_user.role == UserRole.ADMIN:
        query = query.filter(Task.assigned_to == assigned_to)
    if task_status:
        query = query.filter(Task.status == task_status)
    if priority:
        query = query.filter(Task.priority == priority)
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [_task_dict(t, db) for t in tasks],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="ایجاد وظیفه")
def create_task(
    body: TaskCreate,
    request: Request,
    current_user: User = Depends(require_permission(P.TASKS_CREATE)),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail={"success": False, "message": "پروژه یافت نشد"})

    task = Task(
        project_id=body.project_id,
        stage_id=body.stage_id,
        title=body.title,
        description=body.description,
        assigned_to=body.assigned_to,
        created_by=current_user.id,
        priority=body.priority,
        start_date=body.start_date,
        deadline=body.deadline,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_action(
        db=db, user_id=current_user.id, action="TASK_CREATED",
        entity_type="task", entity_id=task.id,
        description=f"وظیفه '{task.title}' ایجاد شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _task_dict(task, db)}


@router.get("/{task_id}", summary="جزئیات وظیفه")
def get_task(
    task_id: int,
    current_user: User = Depends(require_permission(P.TASKS_VIEW)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    _check_task_access(task, current_user)
    return {"success": True, "data": _task_dict(task, db)}


@router.put("/{task_id}", summary="ویرایش وظیفه")
def update_task(
    task_id: int,
    body: TaskUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.TASKS_EDIT)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    log_action(
        db=db, user_id=current_user.id, action="TASK_UPDATED",
        entity_type="task", entity_id=task.id,
        description=f"وظیفه '{task.title}' ویرایش شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _task_dict(task, db)}


@router.delete("/{task_id}", summary="حذف وظیفه")
def delete_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(require_permission(P.TASKS_DELETE)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    db.delete(task)
    db.commit()
    return {"success": True, "message": "وظیفه با موفقیت حذف شد"}


@router.patch("/{task_id}/status", summary="تغییر وضعیت وظیفه")
def update_task_status(
    task_id: int,
    body: TaskStatusUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.TASKS_EDIT)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)

    allowed = VALID_TRANSITIONS.get(task.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "message": f"انتقال از '{task.status.value}' به '{body.status.value}' مجاز نیست",
                "code": "INVALID_TRANSITION",
            },
        )

    task.status = body.status
    if body.status == TaskStatus.DONE:
        task.completed_at = datetime.now(timezone.utc)

    db.commit()

    log_action(
        db=db, user_id=current_user.id, action="TASK_STATUS_CHANGED",
        entity_type="task", entity_id=task.id,
        description=f"وضعیت وظیفه '{task.title}' به '{body.status.value}' تغییر یافت",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _task_dict(task, db)}


@router.patch("/{task_id}/progress", summary="بروزرسانی پیشرفت وظیفه")
def update_progress(
    task_id: int,
    body: TaskProgressUpdate,
    current_user: User = Depends(require_permission(P.TASKS_EDIT)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    task.progress = body.progress
    db.commit()
    return {"success": True, "data": {"progress": task.progress}}


@router.post("/{task_id}/submit", summary="ارسال وظیفه برای بررسی")
def submit_task(
    task_id: int,
    body: TaskSubmit,
    request: Request,
    current_user: User = Depends(require_permission(P.TASKS_SUBMIT)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)

    # Only the assignee can submit
    if task.assigned_to != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "فقط کاربر تخصیص‌یافته می‌تواند وظیفه را ارسال کند", "code": "NOT_ASSIGNEE"},
        )

    if task.status not in [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.NEEDS_REVISION]:
        raise HTTPException(
            status_code=422,
            detail={"success": False, "message": "وضعیت فعلی وظیفه اجازه ارسال را نمی‌دهد", "code": "INVALID_STATUS"},
        )

    task.status = TaskStatus.SUBMITTED
    task.submitted_at = datetime.now(timezone.utc)

    if body.progress is not None:
        task.progress = body.progress

    db.commit()

    log_action(
        db=db, user_id=current_user.id, action="TASK_SUBMITTED",
        entity_type="task", entity_id=task.id,
        description=f"وظیفه '{task.title}' ارسال شد. {body.comment or ''}",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _task_dict(task, db)}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"success": False, "message": "وظیفه یافت نشد"})
    return task


def _check_task_access(task: Task, user: User):
    if user.role == UserRole.ADMIN:
        return
    if task.assigned_to != user.id:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "دسترسی به این وظیفه مجاز نیست", "code": "ACCESS_DENIED"},
        )


def _task_dict(task: Task, db: Session) -> dict:
    latest_eval = (
        db.query(Evaluation)
        .filter(Evaluation.task_id == task.id)
        .order_by(Evaluation.created_at.desc())
        .first()
    )

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "project_id": task.project_id,
        "stage_id": task.stage_id,
        "assigned_to": task.assigned_to,
        "created_by": task.created_by,
        "priority": task.priority.value,
        "status": task.status.value,
        "progress": task.progress,
        "start_date": task.start_date.isoformat() if task.start_date else None,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "assignee_name": task.assignee.full_name if task.assignee else None,
        "project_name": task.project.name if task.project else None,
        "stage_name": task.stage.name if task.stage else None,
        "latest_score": float(latest_eval.score) if latest_eval else None,
    }
