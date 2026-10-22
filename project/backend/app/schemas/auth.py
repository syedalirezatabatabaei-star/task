from pydantic import BaseModel
from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    user_id: int
    username: str
    role: UserRole


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
