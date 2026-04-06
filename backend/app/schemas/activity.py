from datetime import datetime

from pydantic import BaseModel, Field, model_validator

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
    picture_urls: list[str]


class ActivityCreate(BaseModel):
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_time_range(self) -> ActivityCreate:
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class ActivityUpdate(BaseModel):
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)
    start_time: datetime
    end_time: datetime
    picture_urls: list[str]

    @model_validator(mode="after")
    def validate_time_range(self) -> ActivityUpdate:
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self
