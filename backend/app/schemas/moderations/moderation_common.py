from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.moderations.moderation_common import ModerateStatusEnum
from app.schemas.generic import IdMixin


class RequestModeratePublic(BaseModel):
    moderate_status: ModerateStatusEnum = Field(...)


class RequestModerate(RequestModeratePublic):
    model_config = ConfigDict(from_attributes=True)

    moderator_id: int = Field(...)
    moderate_at: datetime = Field(...)


class RequestInfoBase(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderate_status: ModerateStatusEnum = Field(...)
    moderate_at: datetime | None = Field(None)

    requestor_id: int = Field(...)
    request_at: datetime = Field(...)
