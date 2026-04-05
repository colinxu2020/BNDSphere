from datetime import datetime

from pydantic import BaseModel, Field

from app.core import constants
from app.models.activity import ActivityStatusEnum


class ActivityBase(BaseModel):
    id: int
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    club_id: int


class ActivityInfo(ActivityBase):
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)
    start_time: datetime
    end_time: datetime
    status: ActivityStatusEnum
    picture_urls: list[str] | None


class ActivityCreate(BaseModel):
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    club_id: int
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)
    start_time: datetime
    end_time: datetime


class ActivityUpdate(BaseModel):
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    picture_urls: list[str] | None
