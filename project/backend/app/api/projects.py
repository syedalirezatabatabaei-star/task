from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectStatus
from app.models.task import Task, TaskStatus
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberAdd
from app.api.deps import get_current_user, require_permission, get_client_ip
from app.services.audit_service import log_action
from app.core import permissions as P

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", summary="لیست پروژه‌ها")
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    proj_status: Optional[ProjectStatus] = Query(None, alias="status"),
    current_user: User = Depends(require_permission(P.PROJECTS_VIEW)),
    db: Session = Depends(get_db),
):
    from app.models.user import UserRole
    query = db.query(Project)

    # Non-admin users only see projects they're members of
    if current_user.role != UserRole.ADMIN:
        query = query.join(
            ProjectMember,
            (ProjectMember.project_id == Project.id) & (ProjectMember.user_id == current_user.id),
        )

    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    if proj_status:
        query = query.filter(Project.status == proj_status)

    total = query.count()
    projects = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [_project_summary(p, db) for p in projects],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="ایجاد پروژه")
def create_project(
    body: ProjectCreate,
    request: Request,
    current_user: User = Depends(require_permission(P.PROJECTS_CREATE)),
    db: Session = Depends(get_db),
):
    project = Project(
        name=body.name,
        description=body.description,
        status=body.status,
        start_date=body.start_date,
        end_date=body.end_date,
        show_roadmap=body.show_roadmap,
        created_by=current_user.id,
    )
    db.add(project)
    db.flush()

    # Add the creator in the same transaction so a failed membership insert
    # cannot leave an orphan project behind.
    member = ProjectMember(project_id=project.id, user_id=current_user.id, project_role="مدیر پروژه")
    db.add(member)
    db.commit()
    db.refresh(project)

    log_action(
        db=db, user_id=current_user.id, action="PROJECT_CREATED",
        entity_type="project", entity_id=project.id,
        description=f"پروژه '{project.name}' ایجاد شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _project_summary(project, db)}


@router.get("/{project_id}", summary="جزئیات پروژه")
def get_project(
    project_id: int,
    current_user: User = Depends(require_permission(P.PROJECTS_VIEW)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_project_access(project, current_user, db)

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    stages = project.stages

    return {
        "success": True,
        "data": {
            **_project_summary(project, db),
            "members": [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "project_role": m.project_role,
                    "joined_at": m.joined_at.isoformat(),
                    "user": {
                        "id": m.user.id,
                        "username": m.user.username,
                        "full_name": m.user.full_name,
                        "email": m.user.email,
                    } if m.user else None,
                }
                for m in members
            ],
            "stages": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "order_index": s.order_index,
                    "start_date": s.start_date.isoformat() if s.start_date else None,
                    "end_date": s.end_date.isoformat() if s.end_date else None,
                    "task_count": len(s.tasks),
                    "completed_task_count": sum(1 for t in s.tasks if t.status == TaskStatus.DONE),
                }
                for s in stages
            ],
        },
    }


@router.put("/{project_id}", summary="ویرایش پروژه")
def update_project(
    project_id: int,
    body: ProjectUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.PROJECTS_EDIT)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_project_access(project, current_user, db)

    updates = body.model_dump(exclude_unset=True)
    if updates.get('start_date') and updates.get('end_date') and updates['end_date'] < updates['start_date']:
        raise HTTPException(status_code=422, detail={'success': False, 'message': 'تاریخ پایان نمی‌تواند قبل از شروع باشد'})
    for field, value in updates.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    log_action(
        db=db, user_id=current_user.id, action="PROJECT_UPDATED",
        entity_type="project", entity_id=project.id,
        description=f"پروژه '{project.name}' ویرایش شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _project_summary(project, db)}


@router.delete("/{project_id}", summary="حذف پروژه")
def delete_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(require_permission(P.PROJECTS_DELETE)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_project_access(project, current_user, db)

    log_action(
        db=db, user_id=current_user.id, action="PROJECT_DELETED",
        entity_type="project", entity_id=project.id,
        description=f"پروژه '{project.name}' حذف شد",
        ip_address=get_client_ip(request),
    )

    db.delete(project)
    db.commit()
    return {"success": True, "message": "پروژه با موفقیت حذف شد"}


# ─── Members ───────────────────────────────────────────────────────────────────

@router.get("/{project_id}/members", summary="اعضای پروژه")
def list_members(
    project_id: int,
    current_user: User = Depends(require_permission(P.PROJECTS_VIEW)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_project_access(project, current_user, db)

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    return {
        "success": True,
        "data": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "project_role": m.project_role,
                "joined_at": m.joined_at.isoformat(),
                "user": {
                    "id": m.user.id,
                    "username": m.user.username,
                    "full_name": m.user.full_name,
                } if m.user else None,
            }
            for m in members
        ],
    }


@router.post("/{project_id}/members", summary="افزودن عضو به پروژه")
def add_member(
    project_id: int,
    body: ProjectMemberAdd,
    request: Request,
    current_user: User = Depends(require_permission(P.PROJECTS_MEMBERS_MANAGE)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_project_access(project, current_user, db)

    user = db.query(User).filter(User.id == body.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail={"success": False, "message": "کاربر یافت نشد"})

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == body.user_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"success": False, "message": "این کاربر قبلاً به پروژه اضافه شده است", "code": "ALREADY_MEMBER"},
        )

    member = ProjectMember(project_id=project_id, user_id=body.user_id, project_role=body.project_role)
    db.add(member)
    db.commit()

    log_action(
        db=db, user_id=current_user.id, action="PROJECT_MEMBER_ADDED",
        entity_type="project", entity_id=project_id,
        description=f"کاربر {user.username} به پروژه '{project.name}' اضافه شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "message": "عضو با موفقیت اضافه شد"}


@router.delete("/{project_id}/members/{user_id}", summary="حذف عضو از پروژه")
def remove_member(
    project_id: int,
    user_id: int,
    request: Request,
    current_user: User = Depends(require_permission(P.PROJECTS_MEMBERS_MANAGE)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_project_access(project, current_user, db)
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail={"success": False, "message": "عضو یافت نشد"})

    member_name = member.user.username if member.user else str(user_id)
    db.delete(member)
    db.commit()
    log_action(
        db=db, user_id=current_user.id, action="PROJECT_MEMBER_REMOVED",
        entity_type="project", entity_id=project_id,
        description=f"کاربر {member_name} از پروژه '{project.name}' حذف شد",
        ip_address=get_client_ip(request),
    )
    return {"success": True, "message": "عضو با موفقیت حذف شد"}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": "پروژه یافت نشد", "code": "NOT_FOUND"},
        )
    return project


def _check_project_access(project: Project, user: User, db: Session):
    from app.models.user import UserRole
    if user.role == UserRole.ADMIN:
        return
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "شما عضو این پروژه نیستید", "code": "NOT_MEMBER"},
        )


def _project_summary(project: Project, db: Session) -> dict:
    member_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()
    task_count = db.query(Task).filter(Task.project_id == project.id).count()
    done_count = db.query(Task).filter(
        Task.project_id == project.id, Task.status == TaskStatus.DONE
    ).count()

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status.value,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "show_roadmap": project.show_roadmap,
        "created_by": project.created_by,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "member_count": member_count,
        "task_count": task_count,
        "completed_task_count": done_count,
        "progress": round((done_count / task_count * 100) if task_count > 0 else 0),
    }
