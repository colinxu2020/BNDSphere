from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.moderations.moderation_common import ModerateStatusEnum


class RequestModeratePublic(BaseModel):
    moderate_status: ModerateStatusEnum = Field(...)


class RequestModerate(RequestModeratePublic):
    model_config = ConfigDict(from_attributes=True)

    moderator_id: int = Field(...)
    moderate_at: datetime = Field(...)
