from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: int
    stage_id: Optional[int] = None
    assigned_to: Optional[int] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    start_date: Optional[date] = None
    deadline: Optional[date] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("عنوان وظیفه نمی‌تواند خالی باشد")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValueError("مهلت انجام نمی‌تواند قبل از تاریخ شروع باشد")
        return self


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    stage_id: Optional[int] = None
    assigned_to: Optional[int] = None
    priority: Optional[TaskPriority] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskProgressUpdate(BaseModel):
    progress: int

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("پیشرفت باید بین ۰ و ۱۰۰ باشد")
        return v


class TaskSubmit(BaseModel):
    comment: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    project_id: int
    stage_id: Optional[int] = None
    assigned_to: Optional[int] = None
    created_by: Optional[int] = None
    priority: TaskPriority
    status: TaskStatus
    progress: int
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    assignee_name: Optional[str] = None
    project_name: Optional[str] = None
    stage_name: Optional[str] = None
    latest_score: Optional[float] = None

    model_config = {"from_attributes": True}
