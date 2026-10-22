from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus, ProjectMember
from app.models.task import Task, TaskStatus
from app.api.deps import get_current_user, require_permission, require_admin
from app.core import permissions as P

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", summary="داشبورد مدیر")
def admin_dashboard(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    today = date.today()

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.status == ProjectStatus.ACTIVE).count()
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == TaskStatus.DONE).count()
    pending_tasks = db.query(Task).filter(Task.status == TaskStatus.TODO).count()
    in_progress_tasks = db.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS).count()
    submitted_tasks = db.query(Task).filter(Task.status == TaskStatus.SUBMITTED).count()
    needs_revision_tasks = db.query(Task).filter(Task.status == TaskStatus.NEEDS_REVISION).count()
    approved_tasks = db.query(Task).filter(Task.status == TaskStatus.APPROVED).count()
    overdue_tasks = db.query(Task).filter(
        Task.deadline < today,
        Task.status.not_in([TaskStatus.DONE, TaskStatus.APPROVED]),
    ).count()

    # Recent tasks
    recent_tasks = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )

    # Task status distribution
    status_distribution = {
        "TODO": pending_tasks,
        "IN_PROGRESS": in_progress_tasks,
        "SUBMITTED": submitted_tasks,
        "NEEDS_REVISION": needs_revision_tasks,
        "APPROVED": approved_tasks,
        "DONE": completed_tasks,
    }

    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "active_users": active_users,
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "submitted_tasks": submitted_tasks,
            "needs_revision_tasks": needs_revision_tasks,
            "approved_tasks": approved_tasks,
            "overdue_tasks": overdue_tasks,
            "status_distribution": status_distribution,
            "recent_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "assignee_name": t.assignee.full_name if t.assignee else None,
                    "project_name": t.project.name if t.project else None,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                }
                for t in recent_tasks
            ],
        },
    }


@router.get("/user", summary="داشبورد کاربر")
def user_dashboard(
    current_user: User = Depends(require_permission(P.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    today = date.today()

    my_tasks = db.query(Task).filter(Task.assigned_to == current_user.id)
    total_tasks = my_tasks.count()
    todo_tasks = my_tasks.filter(Task.status == TaskStatus.TODO).count()
    in_progress = my_tasks.filter(Task.status == TaskStatus.IN_PROGRESS).count()
    submitted = my_tasks.filter(Task.status == TaskStatus.SUBMITTED).count()
    needs_revision = my_tasks.filter(Task.status == TaskStatus.NEEDS_REVISION).count()
    approved = my_tasks.filter(Task.status == TaskStatus.APPROVED).count()
    done = my_tasks.filter(Task.status == TaskStatus.DONE).count()
    overdue = my_tasks.filter(
        Task.deadline < today,
        Task.status.not_in([TaskStatus.DONE, TaskStatus.APPROVED]),
    ).count()

    # My projects
    my_project_ids = (
        db.query(ProjectMember.project_id)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    )
    my_project_count = len(my_project_ids)

    # Upcoming deadlines (next 7 days)
    from datetime import timedelta
    next_week = today + timedelta(days=7)
    upcoming = (
        db.query(Task)
        .filter(
            Task.assigned_to == current_user.id,
            Task.deadline >= today,
            Task.deadline <= next_week,
            Task.status.not_in([TaskStatus.DONE, TaskStatus.APPROVED]),
        )
        .order_by(Task.deadline)
        .limit(5)
        .all()
    )

    # Recent evaluations
    from app.models.evaluation import Evaluation
    recent_evals = (
        db.query(Evaluation)
        .join(Task, Task.id == Evaluation.task_id)
        .filter(Task.assigned_to == current_user.id)
        .order_by(Evaluation.created_at.desc())
        .limit(3)
        .all()
    )

    # Average score
    from sqlalchemy import func as sqlfunc
    avg_score = (
        db.query(sqlfunc.avg(Evaluation.score))
        .join(Task, Task.id == Evaluation.task_id)
        .filter(Task.assigned_to == current_user.id)
        .scalar()
    )

    return {
        "success": True,
        "data": {
            "user": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "username": current_user.username,
            },
            "tasks": {
                "total": total_tasks,
                "todo": todo_tasks,
                "in_progress": in_progress,
                "submitted": submitted,
                "needs_revision": needs_revision,
                "approved": approved,
                "done": done,
                "overdue": overdue,
            },
            "my_project_count": my_project_count,
            "average_score": round(float(avg_score), 2) if avg_score else None,
            "upcoming_deadlines": [
                {
                    "id": t.id,
                    "title": t.title,
                    "deadline": t.deadline.isoformat(),
                    "priority": t.priority.value,
                    "status": t.status.value,
                    "project_name": t.project.name if t.project else None,
                }
                for t in upcoming
            ],
            "recent_evaluations": [
                {
                    "id": e.id,
                    "task_title": e.task.title if e.task else None,
                    "score": float(e.score),
                    "comment": e.comment,
                    "created_at": e.created_at.isoformat(),
                }
                for e in recent_evals
            ],
        },
    }
