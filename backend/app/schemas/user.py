from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator

from app.core import constants
from app.models.user import RoleEnum, UserGradeEnum
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.upload import AvatarUri


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
    grade: UserGradeEnum | None
    created_at: datetime


class PublicUserInfo(UserBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    avatar_uri: HttpUrl | None = Field(..., max_length=255)
    description: str = Field(..., max_length=constants.USER_MAX_DESCRIPTION_LENGTH)
    grade: UserGradeEnum | None
    created_at: datetime


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str | None = Field(None)
    email: EmailStr | None = Field(None, max_length=constants.USER_MAX_EMAIL_LENGTH)
    avatar_uri: AvatarUri = Field(None, max_length=255)
    description: str | None = Field(
        None,
        max_length=constants.USER_MAX_DESCRIPTION_LENGTH,
    )
    role: RoleEnum | None = Field(None)
    grade: UserGradeEnum | None = Field(None)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(
            self,
            {"username", "description", "role"},
        )
        return self


class Token(BaseModel):
    access_token: str
    token_type: str
