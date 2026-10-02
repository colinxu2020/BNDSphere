from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.core import constants
from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import UserGradeEnum
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.general_activities import ClubGeneralActivityInfo
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.upload import LogoUri

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.clubmember import ClubMember


class ClubBase(BaseModel):
    name: str = Field(..., max_length=constants.CLUB_MAX_NAME_LENGTH)
    category: ClubCategoryEnum = Field(...)
    summary: str = Field(..., max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str = Field(..., max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH)
    logo_uri: HttpUrl | None = Field(None, max_length=255)


class ClubRef(IdMixin, BaseModel):
    """Ref 档: 只含 id 与 name, 用于下拉选择与被其它实体内嵌引用."""

    model_config = ConfigDict(from_attributes=True)

    name: str


class ClubSummary(ClubBase, IdMixin):
    """Summary 档: 列表一行所需的字段, 不携带任何集合; 额外携带社长与副社长."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum
    president: ClubMemberUserInfo | None
    vice_presidents: list[ClubMemberUserInfo]

    _LEADER_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"president", "vice_presidents"},
    )

    @classmethod
    def from_club(cls, club: Club, leaders: Sequence[ClubMember]) -> Self:
        """由社团本身与其社长/副社长成员行组装, 不读取 club.members."""
        president = next(
            (m for m in leaders if m.membership == ClubMembershipEnum.president),
            None,
        )
        return cls.model_validate(
            {
                **{
                    name: getattr(club, name)
                    for name in cls.model_fields
                    if name not in cls._LEADER_FIELDS
                },
                "president": president.user if president is not None else None,
                "vice_presidents": [
                    m.user
                    for m in leaders
                    if m.membership == ClubMembershipEnum.vice_president
                ],
            },
        )


class ClubInfo(ClubBase, IdMixin):
    """Info 档: 完整形状, 含关联集合; 只由详情类接口返回."""

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class UserClubMembership(BaseModel):
    """当前用户在一个社团中的角色, 连同该社团的 Summary."""

    membership: ClubMembershipEnum
    club: ClubSummary


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
