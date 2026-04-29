from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.core import constants
from app.models.user import RoleEnum
from app.schemas.generic import IdMixin


class UserBase(BaseModel):
    username: str = Field(..., max_length=constants.USER_MAX_USERNAME_LENGTH)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserInfo(UserBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr | None = Field(..., max_length=constants.USER_MAX_EMAIL_LENGTH)
    avatar_uri: HttpUrl | None = Field(..., max_length=255)
    description: str = Field(..., max_length=constants.USER_MAX_DESCRIPTION_LENGTH)
    role: RoleEnum
    created_at: datetime


class UserUpdate(BaseModel):
    username: str | None = Field(None)
    email: EmailStr | None = Field(None, max_length=constants.USER_MAX_EMAIL_LENGTH)
    avatar_uri: HttpUrl | None = Field(None, max_length=255)
    description: str | None = Field(
        None,
        max_length=constants.USER_MAX_DESCRIPTION_LENGTH,
    )


class AdminUserUpdate(UserUpdate):
    role: RoleEnum | None = Field(None)


class Token(BaseModel):
    access_token: str
    token_type: str
