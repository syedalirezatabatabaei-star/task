import enum
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Text, Integer, Date, DateTime,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    NEEDS_REVISION = "NEEDS_REVISION"
    APPROVED = "APPROVED"
    DONE = "DONE"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("project_stages.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    assigned_to: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, native_enum=False),
        nullable=False,
        default=TaskPriority.MEDIUM
    )

    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, native_enum=False),
        nullable=False,
        default=TaskStatus.TODO
    )

    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    stage: Mapped["ProjectStage | None"] = relationship("ProjectStage", back_populates="tasks")
    assignee: Mapped["User | None"] = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to])
    creator: Mapped["User | None"] = relationship("User", back_populates="created_tasks", foreign_keys=[created_by])
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation", back_populates="task", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )
