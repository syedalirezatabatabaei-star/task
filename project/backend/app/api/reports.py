from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus
from app.models.evaluation import Evaluation
from app.api.deps import get_current_user, require_permission
from app.core import permissions as P

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/users/{user_id}", summary="گزارش کاربر")
def user_report(
    user_id: int,
    current_user: User = Depends(require_permission(P.REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    from app.models.user import UserRole

    # Non-admins can only see their own report
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "دسترسی به این گزارش مجاز نیست"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail={"success": False, "message": "کاربر یافت نشد"})

    today = date.today()
    task_query = db.query(Task).filter(Task.assigned_to == user_id)
    if current_user.role != UserRole.ADMIN:
        task_query = task_query.join(
            ProjectMember,
            (ProjectMember.project_id == Task.project_id) & (ProjectMember.user_id == current_user.id),
        )
    tasks = task_query.all()
    visible_task_ids = [task.id for task in tasks]
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    approved = sum(1 for t in tasks if t.status == TaskStatus.APPROVED)
    in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    needs_revision = sum(1 for t in tasks if t.status == TaskStatus.NEEDS_REVISION)
    submitted = sum(1 for t in tasks if t.status == TaskStatus.SUBMITTED)
    overdue = sum(
        1 for t in tasks
        if t.deadline and t.deadline < today and t.status not in [TaskStatus.DONE, TaskStatus.APPROVED]
    )
    completion_rate = round((done + approved) / total * 100, 1) if total > 0 else 0

    avg_score = (
        db.query(func.avg(Evaluation.score))
        .join(Task, Task.id == Evaluation.task_id)
        .filter(Task.id.in_(visible_task_ids) if visible_task_ids else Task.id == -1)
        .scalar()
    )

    evaluations = (
        db.query(Evaluation)
        .join(Task, Task.id == Evaluation.task_id)
        .filter(Task.id.in_(visible_task_ids) if visible_task_ids else Task.id == -1)
        .order_by(Evaluation.created_at.desc())
        .all()
    )

    project_ids = {t.project_id for t in tasks}
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []

    return {
        "success": True,
        "data": {
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
            },
            "statistics": {
                "total_tasks": total,
                "done": done,
                "approved": approved,
                "in_progress": in_progress,
                "submitted": submitted,
                "needs_revision": needs_revision,
                "overdue": overdue,
                "completion_rate": completion_rate,
                "average_score": round(float(avg_score), 2) if avg_score else None,
            },
            "projects": [
                {"id": p.id, "name": p.name, "status": p.status.value}
                for p in projects
            ],
            "evaluation_history": [
                {
                    "id": e.id,
                    "task_id": e.task_id,
                    "task_title": e.task.title if e.task else None,
                    "score": float(e.score),
                    "comment": e.comment,
                    "strengths": e.strengths,
                    "weaknesses": e.weaknesses,
                    "created_at": e.created_at.isoformat(),
                }
                for e in evaluations
            ],
        },
    }


@router.get("/projects/{project_id}", summary="گزارش پروژه")
def project_report(
    project_id: int,
    current_user: User = Depends(require_permission(P.REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    from app.models.user import UserRole

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail={"success": False, "message": "پروژه یافت نشد"})

    # Non-admins must be project members
    if current_user.role != UserRole.ADMIN:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail={"success": False, "message": "دسترسی ندارید"})

    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    today = date.today()

    by_status = {}
    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

    by_priority = {}
    for t in tasks:
        by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1

    overdue = sum(
        1 for t in tasks
        if t.deadline and t.deadline < today and t.status not in [TaskStatus.DONE, TaskStatus.APPROVED]
    )

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()

    member_stats = []
    for m in members:
        if not m.user:
            continue
        u = m.user
        u_tasks = [t for t in tasks if t.assigned_to == u.id]
        u_done = sum(1 for t in u_tasks if t.status in [TaskStatus.DONE, TaskStatus.APPROVED])
        avg = (
            db.query(func.avg(Evaluation.score))
            .join(Task, Task.id == Evaluation.task_id)
            .filter(Task.assigned_to == u.id, Task.project_id == project_id)
            .scalar()
        )
        member_stats.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "project_role": m.project_role,
            "total_tasks": len(u_tasks),
            "completed_tasks": u_done,
            "average_score": round(float(avg), 2) if avg else None,
        })

    return {
        "success": True,
        "data": {
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.status.value,
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None,
            },
            "task_summary": {
                "total": len(tasks),
                "by_status": by_status,
                "by_priority": by_priority,
                "overdue": overdue,
            },
            "member_stats": member_stats,
        },
    }
