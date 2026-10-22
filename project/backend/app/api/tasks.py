from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.project_stage import ProjectStage
from app.models.evaluation import Evaluation
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskProgressUpdate, TaskSubmit
from app.api.deps import get_current_user, require_permission, get_client_ip, get_user_permission_codes
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

    # Non-admins only see tasks assigned to them inside projects they belong to.
    if current_user.role != UserRole.ADMIN:
        query = query.join(
            ProjectMember,
            (ProjectMember.project_id == Task.project_id) & (ProjectMember.user_id == current_user.id),
        ).filter(Task.assigned_to == current_user.id)

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

    if current_user.role != UserRole.ADMIN:
        membership = db.query(ProjectMember.id).filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail={"success": False, "message": "برای ایجاد وظیفه باید عضو پروژه باشید", "code": "NOT_MEMBER"})

    if body.stage_id is not None:
        stage = db.query(ProjectStage).filter(
            ProjectStage.id == body.stage_id,
            ProjectStage.project_id == project.id,
        ).first()
        if not stage:
            raise HTTPException(status_code=400, detail={"success": False, "message": "مرحله انتخاب‌شده متعلق به این پروژه نیست", "code": "INVALID_STAGE"})

    if body.assigned_to is not None:
        assignee = db.query(User).filter(User.id == body.assigned_to, User.is_active == True).first()
        if not assignee:
            raise HTTPException(status_code=404, detail={"success": False, "message": "کاربر تخصیص‌یافته یافت نشد یا غیرفعال است", "code": "INVALID_ASSIGNEE"})
        assignee_membership = db.query(ProjectMember.id).filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == body.assigned_to,
        ).first()
        if not assignee_membership and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=400, detail={"success": False, "message": "کاربر تخصیص‌یافته عضو پروژه نیست", "code": "ASSIGNEE_NOT_MEMBER"})

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
    _check_task_access(task, current_user, db)
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
    _check_task_access(task, current_user)

    updates = body.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is None:
        raise HTTPException(status_code=422, detail={"success": False, "message": "عنوان وظیفه نمی‌تواند خالی باشد"})
    effective_start = updates.get("start_date", task.start_date)
    effective_deadline = updates.get("deadline", task.deadline)
    if effective_start and effective_deadline and effective_deadline < effective_start:
        raise HTTPException(status_code=422, detail={"success": False, "message": "مهلت انجام نمی‌تواند قبل از تاریخ شروع باشد"})
    if updates.get("stage_id") is not None:
        stage = db.query(ProjectStage).filter(
            ProjectStage.id == updates["stage_id"],
            ProjectStage.project_id == task.project_id,
        ).first()
        if not stage:
            raise HTTPException(status_code=400, detail={"success": False, "message": "مرحله انتخاب‌شده متعلق به این پروژه نیست", "code": "INVALID_STAGE"})
    if "assigned_to" in updates and current_user.role != UserRole.ADMIN:
        if P.TASKS_ASSIGN not in get_user_permission_codes(current_user, db):
            raise HTTPException(status_code=403, detail={"success": False, "message": "اجازه تخصیص وظیفه را ندارید", "code": "TASK_ASSIGN_DENIED"})
    if updates.get("assigned_to") is not None:
        assignee = db.query(User).filter(User.id == updates["assigned_to"], User.is_active == True).first()
        if not assignee:
            raise HTTPException(status_code=404, detail={"success": False, "message": "کاربر تخصیص‌یافته یافت نشد یا غیرفعال است", "code": "INVALID_ASSIGNEE"})
        member = db.query(ProjectMember.id).filter(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == updates["assigned_to"],
        ).first()
        if not member and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=400, detail={"success": False, "message": "کاربر تخصیص‌یافته عضو پروژه نیست", "code": "ASSIGNEE_NOT_MEMBER"})

    for field, value in updates.items():
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
    _check_task_access(task, current_user)
    task_title = task.title
    db.delete(task)
    db.commit()
    log_action(
        db=db, user_id=current_user.id, action="TASK_DELETED",
        entity_type="task", entity_id=task_id,
        description=f"وظیفه '{task_title}' حذف شد",
        ip_address=get_client_ip(request),
    )
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
    _check_task_access(task, current_user)

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
    request: Request,
    current_user: User = Depends(require_permission(P.TASKS_EDIT)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    _check_task_access(task, current_user)
    task.progress = body.progress
    db.commit()
    log_action(
        db=db, user_id=current_user.id, action="TASK_PROGRESS_UPDATED",
        entity_type="task", entity_id=task.id,
        description=f"پیشرفت وظیفه '{task.title}' به {task.progress}% تغییر یافت",
        ip_address=get_client_ip(request),
    )
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
    _check_task_access(task, current_user, db)

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


def _check_task_access(task: Task, user: User, db: Session):
    if user.role == UserRole.ADMIN:
        return
    if task.assigned_to != user.id:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "این وظیفه به شما تخصیص داده نشده است", "code": "ACCESS_DENIED"},
        )
    membership = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == task.project_id,
        ProjectMember.user_id == user.id,
    ).first()
    if not membership:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "شما به این پروژه دسترسی ندارید", "code": "PROJECT_ACCESS_DENIED"},
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
