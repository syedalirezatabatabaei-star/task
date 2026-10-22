from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.models.project import ProjectMember
from app.models.evaluation import Evaluation
from app.schemas.evaluation import EvaluationCreate, EvaluationUpdate
from app.api.deps import get_current_user, require_permission, get_client_ip
from app.services.audit_service import log_action
from app.core import permissions as P

router = APIRouter(tags=["Evaluations"])


@router.get("/tasks/{task_id}/evaluations", summary="ارزیابی‌های وظیفه")
def list_evaluations(
    task_id: int,
    current_user: User = Depends(require_permission(P.EVALUATIONS_VIEW)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    _check_task_access(task, current_user)

    evaluations = (
        db.query(Evaluation)
        .filter(Evaluation.task_id == task_id)
        .order_by(Evaluation.created_at.desc())
        .all()
    )
    return {"success": True, "data": [_eval_dict(e) for e in evaluations]}


@router.post("/tasks/{task_id}/evaluations", status_code=status.HTTP_201_CREATED, summary="ایجاد ارزیابی")
def create_evaluation(
    task_id: int,
    body: EvaluationCreate,
    request: Request,
    current_user: User = Depends(require_permission(P.EVALUATIONS_CREATE)),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    _check_evaluation_access(task, current_user, db)
    if current_user.role != UserRole.ADMIN and task.assigned_to == current_user.id:
        raise HTTPException(status_code=403, detail={"success": False, "message": "کاربر تخصیص‌یافته نمی‌تواند ارزیاب وظیفه خودش باشد", "code": "EVALUATOR_REQUIRED"})

    if task.status not in [TaskStatus.SUBMITTED, TaskStatus.APPROVED]:
        raise HTTPException(
            status_code=422,
            detail={"success": False, "message": "فقط وظایف ارسال‌شده را می‌توان ارزیابی کرد", "code": "INVALID_STATUS"},
        )

    evaluation = Evaluation(
        task_id=task_id,
        evaluator_id=current_user.id,
        score=body.score,
        comment=body.comment,
        strengths=body.strengths,
        weaknesses=body.weaknesses,
    )
    db.add(evaluation)

    # Mark task as APPROVED after evaluation
    task.status = TaskStatus.APPROVED
    db.commit()
    db.refresh(evaluation)

    log_action(
        db=db, user_id=current_user.id, action="TASK_EVALUATED",
        entity_type="task", entity_id=task_id,
        description=f"وظیفه '{task.title}' با نمره {body.score} ارزیابی شد",
        ip_address=get_client_ip(request),
    )

    return {"success": True, "data": _eval_dict(evaluation)}


@router.put("/evaluations/{evaluation_id}", summary="ویرایش ارزیابی")
def update_evaluation(
    evaluation_id: int,
    body: EvaluationUpdate,
    request: Request,
    current_user: User = Depends(require_permission(P.EVALUATIONS_EDIT)),
    db: Session = Depends(get_db),
):
    evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail={"success": False, "message": "ارزیابی یافت نشد"})
    task = _get_task_or_404(evaluation.task_id, db)
    _check_evaluation_access(task, current_user, db)
    if current_user.role != UserRole.ADMIN and evaluation.evaluator_id != current_user.id:
        raise HTTPException(status_code=403, detail={"success": False, "message": "فقط ارزیاب ثبت‌کننده می‌تواند ارزیابی را ویرایش کند"})

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(evaluation, field, value)

    db.commit()
    db.refresh(evaluation)
    log_action(db=db, user_id=current_user.id, action="EVALUATION_UPDATED", entity_type="evaluation", entity_id=evaluation.id, description=f"ارزیابی وظیفه {task.id} ویرایش شد", ip_address=get_client_ip(request))
    return {"success": True, "data": _eval_dict(evaluation)}


def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"success": False, "message": "وظیفه یافت نشد"})
    return task


def _check_task_access(task: Task, user: User):
    if user.role == UserRole.ADMIN or task.assigned_to == user.id:
        return
    raise HTTPException(status_code=403, detail={"success": False, "message": "دسترسی به این وظیفه مجاز نیست"})


def _check_evaluation_access(task: Task, user: User, db: Session):
    if user.role == UserRole.ADMIN:
        return
    member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == task.project_id,
        ProjectMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail={"success": False, "message": "فقط اعضای پروژه می‌توانند ارزیابی را مشاهده یا مدیریت کنند"})


def _eval_dict(e: Evaluation) -> dict:
    return {
        "id": e.id,
        "task_id": e.task_id,
        "evaluator_id": e.evaluator_id,
        "evaluator_name": e.evaluator.full_name if e.evaluator else None,
        "score": float(e.score),
        "comment": e.comment,
        "strengths": e.strengths,
        "weaknesses": e.weaknesses,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }
