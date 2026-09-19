from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)

from app.core import constants
from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import UserGradeEnum
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.general_activities import ClubGeneralActivityInfo
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.upload import LogoUri
from app.services.errors import BadRequestError


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
    # Overrides ClubBase.logo_uri: club creation writes straight to the DB with
    # no moderation gate, so it must not accept an arbitrary external URL.
    logo_uri: LogoUri = Field(None, max_length=255)


class AdminClubCreate(ClubCreate):
    # Club import: created_at backdates the club to its real founding time.
    # Kept as a comment, not a docstring: docstrings land in openapi.json.
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_created_at(self) -> Self:
        if self.created_at > datetime.now(UTC):
            raise BadRequestError(
                "error.club.created_at_in_future",
                "CLUB_CREATED_AT_IN_FUTURE",
            )
        return self


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


class ClubMemberUserInfo(IdMixin, BaseModel):
    username: str
    avatar_uri: HttpUrl | None
    grade: UserGradeEnum | None

    model_config = ConfigDict(from_attributes=True)


class ClubMemberInfo(IdMixin, BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum
    updated_at: datetime
    user: ClubMemberUserInfo

    model_config = ConfigDict(from_attributes=True)


class ClubMemberUpdate(BaseModel):
    user_id: int
    club_id: int
    membership: ClubMembershipEnum


class ClubMemberAssignableRoleEnum(StrEnum):
    member = "member"
    vice_president = "vice_president"
    president = "president"


class ClubMemberRoleUpdate(BaseModel):
    membership: ClubMemberAssignableRoleEnum
