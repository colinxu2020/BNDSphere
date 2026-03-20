from datetime import datetime

from pydantic import BaseModel, Field

from app.core.settings import settings
from app.models.user import RoleEnum


class UserCreate(BaseModel):
    username: str = Field(..., max_length=settings.max_username_length)
    password: str = Field(..., min_length=6)

class UserInfo(BaseModel):
    username: str = Field(..., max_length=settings.max_username_length)
    email: str | None = Field(..., max_length=settings.max_email_length)
    avatar_uri: str = Field(..., max_length=255)
    description: str = Field(..., max_length=255)
    role: RoleEnum = Field(...)
    created_at: datetime = Field(...)

