from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.moderations.moderation_common import ModerationStatusEnum
from app.schemas.generic import IdMixin
from app.schemas.moderations.moderation_common import UpdateRequestCreateBase


class UserUpdateUpdateRequestCreate(UpdateRequestCreateBase):
    model_config = ConfigDict(from_attributes=True)

    username: str | None = Field(None)
    avatar_uri: HttpUrl | None = Field(None)
    description: str | None = Field(None)


class UserUpdateRequestInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderate_status: ModerationStatusEnum = Field(...)
    moderate_at: datetime | None = Field(None)

    request_at: datetime = Field(...)

    user_id: int = Field(...)
    username: str | None = Field(None)
    avatar_uri: HttpUrl | None = Field(None)
    description: str | None = Field(None)
