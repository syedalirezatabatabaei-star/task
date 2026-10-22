from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class EvaluationBase(BaseModel):
    score: float
    comment: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("نمره باید بین ۰ و ۱۰۰ باشد")
        return v


class EvaluationCreate(EvaluationBase):
    pass


class EvaluationUpdate(BaseModel):
    score: Optional[float] = None
    comment: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not 0 <= v <= 100:
            raise ValueError("نمره باید بین ۰ و ۱۰۰ باشد")
        return v


class EvaluationResponse(EvaluationBase):
    id: int
    task_id: int
    evaluator_id: Optional[int] = None
    evaluator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
