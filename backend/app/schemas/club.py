from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core import constants
from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.general_activities import ClubGeneralActivityInfo
from app.schemas.generic import IdMixin


class ClubBase(BaseModel):
    name: str = Field(..., max_length=constants.CLUB_MAX_NAME_LENGTH)
    category: ClubCategoryEnum = Field(...)
    summary: str = Field(..., max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str = Field(..., max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH)
    logo_uri: HttpUrl | None = Field(None, max_length=255)


class ClubInfo(ClubBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum
    members: list[ClubMemberInfo]
    club_activities: list[ClubActivityInfo]
    general_activity_records: list[ClubGeneralActivityInfo]


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    summary: str | None = Field(None, max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str | None = Field(
        None,
        max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH,
    )
    logo_uri: HttpUrl | None = Field(None, max_length=255)


class ScfClubUpdate(ClubUpdate):
    star_level: ClubStarLevelEnum | None = Field(None)


class AdminClubUpdate(ScfClubUpdate):
    model_config = ConfigDict(from_attributes=True)

    status: ClubStatusEnum | None = Field(None)


class ClubMemberInfo(IdMixin, BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClubMemberUpdate(BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum
