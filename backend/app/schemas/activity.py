from datetime import datetime

from pydantic import BaseModel, Field

from app.core.settings import settings
from app.models.activity import ActivityStatusEnum


class ActivityBase(BaseModel):
    id: int
    name: str = Field(..., max_length=settings.activity_max_name_length)
    club_id: int


class ActivityInfo(ActivityBase):
    description: str = Field(..., max_length=settings.activity_max_description_length)
    location: str = Field(..., max_length=settings.activity_max_location_length)
    start_time: datetime
    end_time: datetime
    status: ActivityStatusEnum
    picture_urls: list[str] | None


class ActivityCreate(BaseModel):
    name: str = Field(..., max_length=settings.activity_max_name_length)
    club_id: int
    description: str = Field(..., max_length=settings.activity_max_description_length)
    location: str = Field(..., max_length=settings.activity_max_location_length)
    start_time: datetime
    end_time: datetime


class ActivityUpdate(BaseModel):
    description: str = Field(..., max_length=settings.activity_max_description_length)
    picture_urls: list[str] | None
