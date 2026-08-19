from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import UserGradeEnum
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.moderations.moderation_common import UpdateRequestCreateBase
from app.schemas.upload import AvatarUri


class UserUpdateRequestCreate(UpdateRequestCreateBase):
    model_config = ConfigDict(from_attributes=True)

    username: str | None = Field(None)
    avatar_uri: AvatarUri = Field(None)
    description: str | None = Field(None)
    grade: UserGradeEnum | None = Field(None)
    update_fields: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(self, {"username", "description"})
        return self


class UserUpdateRequestInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderation_status: ModerationStatusEnum = Field(...)
    moderate_at: datetime | None = Field(None)

    request_at: datetime = Field(...)

    user_id: int = Field(...)
    username: str | None = Field(None)
    avatar_uri: HttpUrl | None = Field(None)
    description: str | None = Field(None)
    grade: UserGradeEnum | None = Field(None)
