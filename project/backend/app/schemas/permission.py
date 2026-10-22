from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class UserPermissionUpdate(BaseModel):
    permission_codes: list[str]


class UserPermissionResponse(BaseModel):
    id: int
    user_id: int
    permission_id: int
    permission: PermissionResponse
    created_at: datetime

    model_config = {"from_attributes": True}
