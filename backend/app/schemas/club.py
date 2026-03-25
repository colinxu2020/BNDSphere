from datetime import datetime

from pydantic import BaseModel, Field

from app.core.settings import settings
from app.models.club import ClubStarLevelEnum, ClubStatusEnum


class ClubBase(BaseModel):
    id: int
    name: str = Field(..., max_length=settings.club_max_name_length)


class ClubInfo(ClubBase):
    summary: str = Field(..., max_length=settings.club_max_summary_length)
    description: str = Field(..., max_length=settings.club_max_description_length)
    logo_uri: str = Field(..., max_length=255)
    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum


class ClubCreate(ClubBase):
    summary: str = Field(..., max_length=settings.club_max_summary_length)
    description: str = Field(..., max_length=settings.club_max_description_length)
    logo_uri: str = Field(..., max_length=255)
