from datetime import datetime

from pydantic import BaseModel, Field

from app.core.settings import settings
from app.models.club import ClubStatusEnum, ClubStarLevelEnum


class ClubBase(BaseModel):
    name: str = Field(..., max_length=settings.club_max_name_length)


class ClubInfo(ClubBase):
    description: str = Field(..., max_length=settings.club_max_description_length)
    logo_uri: str = Field(..., max_length=255)
    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum
