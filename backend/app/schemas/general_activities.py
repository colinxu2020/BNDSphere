from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.core import constants
from app.models.general_activity import (
    GeneralActivityLevelEnum,
    ParticipationTypeEnum,
)
from app.models.user import AuditStatusEnum
from app.schemas.academic_terms import AcademicTermInfo
from app.schemas.generic import IdMixin
from app.schemas.upload import ActivityPosterUri
from app.services.errors import BadRequestError


class GeneralActivityBase(BaseModel):
    name: str = Field(..., max_length=constants.GENERAL_ACTIVITY_MAX_NAME_LENGTH)
    description: str
    level: GeneralActivityLevelEnum
    starts_at: datetime | None = Field(None)
    ends_at: datetime | None = Field(None)
    poster_uri: HttpUrl | None = Field(None, max_length=2048)
    article_url: str | None = Field(None, max_length=2048)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at < self.starts_at
        ):
            raise BadRequestError(
                "error.general_activity.invalid_time_range",
                "GENERAL_ACTIVITY_INVALID_TIME_RANGE",
            )
        return self


class GeneralActivityCreate(GeneralActivityBase):
    poster_uri: ActivityPosterUri = Field(None, max_length=2048)


class GeneralActivityInfo(GeneralActivityBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    club_records: list[ClubGeneralActivityInfo]
    academic_term: AcademicTermInfo


class GeneralActivityUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = Field(
        None,
        max_length=constants.GENERAL_ACTIVITY_MAX_NAME_LENGTH,
    )
    description: str | None = Field(None)
    level: GeneralActivityLevelEnum | None = Field(None)
    starts_at: datetime | None = Field(None)
    ends_at: datetime | None = Field(None)
    poster_uri: ActivityPosterUri = Field(None, max_length=2048)
    article_url: str | None = Field(None, max_length=2048)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at < self.starts_at
        ):
            raise BadRequestError(
                "error.general_activity.invalid_time_range",
                "GENERAL_ACTIVITY_INVALID_TIME_RANGE",
            )
        return self


class ClubGeneralActivityBase(BaseModel):
    proof_files: list[str]
    created_at: datetime
    audit_status: AuditStatusEnum
    requested_score: int
    participation_type: ParticipationTypeEnum
    met_conditions: list[RecordConditionDetail]
    auditor_id: int | None


class ClubGeneralActivityInfo(ClubGeneralActivityBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    club_id: int
    activity_id: int


class ClubGeneralActivityCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    participation_type: ParticipationTypeEnum
    proof_files: list[str] = Field(default_factory=list)
    requested_score: int


class ClubGeneralActivityUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    participation_type: ParticipationTypeEnum
    proof_files: list[str] = Field(default_factory=list)
    requested_score: int


class FederationRecordUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_status: AuditStatusEnum = Field(...)
    final_score: int | None = Field(None)


class RecordConditionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_met: bool
    record_id: int
    condition_id: int


class ActivityConditionBase(BaseModel):
    description: str
    active: bool


class ActivityConditionCreate(ActivityConditionBase):
    pass


class ActivityConditionInfo(ActivityConditionBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)
