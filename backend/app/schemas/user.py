from datetime import datetime

from pydantic import BaseModel, Field

from app.core.settings import settings
from app.models.user import RoleEnum


class UserBase(BaseModel):
    username: str = Field(..., max_length=settings.user_max_username_length)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserInfo(UserBase):
    id: int
    email: str | None = Field(..., max_length=settings.user_max_email_length)
    avatar_uri: str = Field(..., max_length=255)
    description: str = Field(..., max_length=settings.user_max_description_length)
    role: RoleEnum
    created_at: datetime


class UserUpdate(BaseModel):
    email: str | None = Field(..., max_length=settings.user_max_email_length)
    avatar_uri: str = Field(..., max_length=255)
    description: str = Field(..., max_length=settings.user_max_description_length)


class Token(BaseModel):
    access_token: str
    token_type: str
