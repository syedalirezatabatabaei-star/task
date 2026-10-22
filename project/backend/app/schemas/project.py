from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNED
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    show_roadmap: bool = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    show_roadmap: Optional[bool] = None


class ProjectMemberAdd(BaseModel):
    user_id: int
    project_role: Optional[str] = None


class ProjectMemberResponse(BaseModel):
    id: int
    user_id: int
    project_id: int
    project_role: Optional[str] = None
    joined_at: datetime
    user: Optional[dict] = None

    model_config = {"from_attributes": True}


class ProjectResponse(ProjectBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    task_count: int = 0
    completed_task_count: int = 0

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    members: list[dict] = []
    stages: list[dict] = []

    model_config = {"from_attributes": True}


class StageBase(BaseModel):
    name: str
    description: Optional[str] = None
    order_index: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class StageCreate(StageBase):
    pass


class StageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class StageResponse(StageBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
    completed_task_count: int = 0

    model_config = {"from_attributes": True}
