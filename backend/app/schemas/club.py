from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core import constants
from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum


class ClubBase(BaseModel):
    id: int
    name: str = Field(..., max_length=constants.CLUB_MAX_NAME_LENGTH)
    category: ClubCategoryEnum = Field(...)


class ClubInfo(ClubBase):
    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(..., max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str = Field(..., max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH)
    logo_uri: HttpUrl | None = Field(None, max_length=255)
    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum


class ClubCreate(BaseModel):
    name: str = Field(..., max_length=constants.CLUB_MAX_NAME_LENGTH)
    summary: str = Field(..., max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str = Field(..., max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH)
    logo_uri: HttpUrl | None = Field(None, max_length=255)
    category: ClubCategoryEnum = Field(...)


class ClubUpdate(BaseModel):
    summary: str = Field(..., max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str = Field(..., max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH)
    logo_uri: HttpUrl | None = Field(None, max_length=255)


class ClubMemberRelationship(BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum

    model_config = ConfigDict(from_attributes=True)


class ClubMemberUpdate(BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum
