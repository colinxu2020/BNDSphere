from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.core import constants
from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.general_activities import ClubGeneralActivityInfo
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.upload import LogoUri


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


class ClubSummaryInfo(ClubBase, IdMixin):
    """Card/list representation of a club.

    ClubInfo embeds members, club_activities and general_activity_records, so a
    browse grid of clubs downloads every member of every club just to render a
    count. This is the shape those surfaces actually need, with member_count in
    place of the nested collections.

    Additive: ClubInfo and every endpoint returning it are unchanged.

    member_count counts all membership rows, matching what the previous clients
    computed from `len(members)`. Narrowing it to active members only would change
    a number already shown in the product, so that stays a separate decision.
    """

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum
    member_count: int = Field(..., ge=0)


class ClubCreate(ClubBase):
    # Overrides ClubBase.logo_uri: club creation writes straight to the DB with
    # no moderation gate, so it must not accept an arbitrary external URL.
    logo_uri: LogoUri = Field(None, max_length=255)


class ClubUpdate(BaseModel):
    summary: str | None = Field(None, max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str | None = Field(
        None,
        max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH,
    )
    logo_uri: LogoUri = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(self, {"summary", "description"})
        return self


class FederationClubUpdate(ClubUpdate):
    star_level: ClubStarLevelEnum | None = Field(None)

    @model_validator(mode="after")
    def validate_star_level(self) -> Self:
        ensure_non_nullable_fields_present(self, {"star_level"})
        return self


class AdminClubUpdate(FederationClubUpdate):
    model_config = ConfigDict(from_attributes=True)

    status: ClubStatusEnum | None = Field(None)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        ensure_non_nullable_fields_present(self, {"status"})
        return self


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
