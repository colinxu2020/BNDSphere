from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.core.settings import settings
from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum


class ClubBase(BaseModel):
    id: int
    name: str = Field(..., max_length=settings.club_max_name_length)
    category: ClubCategoryEnum = Field(...)


class ClubInfo(ClubBase):
    summary: str = Field(..., max_length=settings.club_max_summary_length)
    description: str = Field(..., max_length=settings.club_max_description_length)
    logo_uri: HttpUrl | None = Field(None, max_length=255)
    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum


class ClubCreate(BaseModel):
    name: str = Field(..., max_length=settings.club_max_name_length)
    summary: str = Field(..., max_length=settings.club_max_summary_length)
    description: str = Field(..., max_length=settings.club_max_description_length)
    logo_uri: HttpUrl | None = Field(None, max_length=255)
    category: ClubCategoryEnum = Field(...)


class ClubUpdate(BaseModel):
    summary: str = Field(..., max_length=settings.club_max_summary_length)
    description: str = Field(..., max_length=settings.club_max_description_length)
    logo_uri: HttpUrl | None = Field(None, max_length=255)


class ClubMemberUpdate(BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum
