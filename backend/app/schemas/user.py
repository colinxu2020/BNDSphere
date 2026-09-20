from datetime import datetime
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.core import constants
from app.models.user import RoleEnum, UserGradeEnum
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.upload import AvatarUri


class UserBase(BaseModel):
    username: str = Field(..., max_length=constants.USER_MAX_USERNAME_LENGTH)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    accepted_privacy_policy: Literal[True]
    accepted_user_agreement: Literal[True]
    accepted_cross_border_transfer: Literal[True]


class UserRegistration(UserCreate):
    altcha: str = Field(
        ...,
        min_length=1,
        max_length=constants.ALTCHA_MAX_PAYLOAD_LENGTH,
    )


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

    username: str | None = Field(
        None,
        min_length=1,
        max_length=constants.USER_MAX_USERNAME_LENGTH,
    )
    email: EmailStr | None = Field(None, max_length=constants.USER_MAX_EMAIL_LENGTH)
    avatar_uri: AvatarUri = Field(None, max_length=255)
    description: str | None = Field(
        None,
        max_length=constants.USER_MAX_DESCRIPTION_LENGTH,
    )
    role: RoleEnum | None = Field(None)
    grade: UserGradeEnum | None = Field(None)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

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
