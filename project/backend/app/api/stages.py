from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.project_stage import ProjectStage
from app.models.task import Task, TaskStatus
from app.schemas.project import StageCreate, StageUpdate
from app.api.deps import get_current_user, require_permission, get_client_ip
from app.services.audit_service import log_action
from app.core import permissions as P

router = APIRouter(tags=["Stages"])


@router.get("/projects/{project_id}/stages", summary="مراحل پروژه")
def list_stages(
    project_id: int,
    current_user: User = Depends(require_permission(P.STAGES_VIEW)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_access(project, current_user, db)

    stages = (
        db.query(ProjectStage)
        .filter(ProjectStage.project_id == project_id)
        .order_by(ProjectStage.order_index)
        .all()
    )

    return {
        "success": True,
        "data": [_stage_dict(s, db) for s in stages],
    }


@router.post("/projects/{project_id}/stages", status_code=status.HTTP_201_CREATED, summary="ایجاد مرحله")
def create_stage(
    project_id: int,
    body: StageCreate,
    request: Request,
    current_user: User = Depends(require_permission(P.STAGES_CREATE)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_access(project, current_user, db)

    stage = ProjectStage(
        project_id=project_id,
        name=body.name,
        description=body.description,
        order_index=body.order_index,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)

    log_action(
        db=db, user_id=current_user.id, action="STAGE_CREATED",
        entity_type="stage", entity_id=stage.id,
        description=f"مرحله '{stage.name}' در پروژه '{project.name}' ایجاد شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _stage_dict(stage, db)}


@router.put("/stages/{stage_id}", summary="ویرایش مرحله")
def update_stage(
    stage_id: int,
    body: StageUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.STAGES_EDIT)),
    db: Session = Depends(get_db),
):
    stage = _get_stage_or_404(stage_id, db)
    project = _get_project_or_404(stage.project_id, db)
    _check_access(project, current_user, db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(stage, field, value)

    db.commit()
    db.refresh(stage)
    log_action(db=db, user_id=current_user.id, action="STAGE_UPDATED", entity_type="stage", entity_id=stage.id, description=f"مرحله '{stage.name}' ویرایش شد", ip_address=get_client_ip(request))
    return {"success": True, "data": _stage_dict(stage, db)}


@router.delete("/stages/{stage_id}", summary="حذف مرحله")
def delete_stage(
    stage_id: int,
    request: Request,
    current_user: User = Depends(require_permission(P.STAGES_DELETE)),
    db: Session = Depends(get_db),
):
    stage = _get_stage_or_404(stage_id, db)
    project = _get_project_or_404(stage.project_id, db)
    _check_access(project, current_user, db)
    stage_name = stage.name
    db.delete(stage)
    db.commit()
    log_action(db=db, user_id=current_user.id, action="STAGE_DELETED", entity_type="stage", entity_id=stage_id, description=f"مرحله '{stage_name}' حذف شد", ip_address=get_client_ip(request))
    return {"success": True, "message": "مرحله با موفقیت حذف شد"}


# ─── Roadmap ──────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/roadmap", summary="نقشه راه پروژه")
def get_roadmap(
    project_id: int,
    current_user: User = Depends(require_permission(P.ROADMAP_VIEW)),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(project_id, db)
    _check_access(project, current_user, db)

    if not project.show_roadmap:
        raise HTTPException(
            status_code=403,
            detail={"success": False, "message": "نقشه راه این پروژه غیرفعال است", "code": "ROADMAP_DISABLED"},
        )

    stages = (
        db.query(ProjectStage)
        .filter(ProjectStage.project_id == project_id)
        .order_by(ProjectStage.order_index)
        .all()
    )

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
            "stages": [_stage_dict(s, db) for s in stages],
        },
    }


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_project_or_404(project_id: int, db: Session) -> Project:
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"success": False, "message": "پروژه یافت نشد"})
    return p


def _get_stage_or_404(stage_id: int, db: Session) -> ProjectStage:
    s = db.query(ProjectStage).filter(ProjectStage.id == stage_id).first()
    if not s:
        raise HTTPException(status_code=404, detail={"success": False, "message": "مرحله یافت نشد"})
    return s


def _check_access(project: Project, user: User, db: Session):
    from app.models.user import UserRole
    if user.role == UserRole.ADMIN:
        return
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail={"success": False, "message": "دسترسی ندارید"})


def _stage_dict(stage: ProjectStage, db: Session) -> dict:
    tasks = db.query(Task).filter(Task.stage_id == stage.id).all()
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    return {
        "id": stage.id,
        "project_id": stage.project_id,
        "name": stage.name,
        "description": stage.description,
        "order_index": stage.order_index,
        "start_date": stage.start_date.isoformat() if stage.start_date else None,
        "end_date": stage.end_date.isoformat() if stage.end_date else None,
        "created_at": stage.created_at.isoformat(),
        "task_count": len(tasks),
        "completed_task_count": done,
        "progress": round((done / len(tasks) * 100) if tasks else 0),
    }
