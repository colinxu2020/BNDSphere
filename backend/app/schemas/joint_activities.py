from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core import constants
from app.models.user import AuditStatusEnum
from app.schemas.academic_terms import AcademicTermInfo
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.schemas.upload import JointActivityArchiveUri
from app.services.errors import BadRequestError


class JointActivityClubInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class JointActivityParticipationInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    club_id: int
    registered_by_user_id: int
    is_initiator: bool
    created_at: datetime
    club: JointActivityClubInfo


class JointActivityBase(BaseModel):
    name: str = Field(..., max_length=constants.JOINT_ACTIVITY_MAX_NAME_LENGTH)
    description: str
    location: str = Field(
        ...,
        max_length=constants.JOINT_ACTIVITY_MAX_LOCATION_LENGTH,
    )
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise BadRequestError(
                "error.joint_activity.invalid_time_range",
                "JOINT_ACTIVITY_INVALID_TIME_RANGE",
            )
        return self


class JointActivityCreate(JointActivityBase):
    pass


class JointActivityUpdate(BaseModel):
    name: str | None = Field(
        None,
        max_length=constants.JOINT_ACTIVITY_MAX_NAME_LENGTH,
    )
    description: str | None = None
    location: str | None = Field(
        None,
        max_length=constants.JOINT_ACTIVITY_MAX_LOCATION_LENGTH,
    )
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        ensure_non_nullable_fields_present(
            self,
            {"name", "description", "location", "starts_at", "ends_at"},
        )
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise BadRequestError(
                "error.joint_activity.invalid_time_range",
                "JOINT_ACTIVITY_INVALID_TIME_RANGE",
            )
        return self


class JointActivityArchiveUpdate(BaseModel):
    archive_text: str | None = None
    archive_files: list[JointActivityArchiveUri] = Field(
        default_factory=list,
        max_length=20,
    )


class JointActivityPreliminaryReview(BaseModel):
    status: AuditStatusEnum

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.status == AuditStatusEnum.pending:
            raise BadRequestError(
                "error.joint_activity.review_decision_required",
                "JOINT_ACTIVITY_REVIEW_DECISION_REQUIRED",
            )
        return self


class JointActivityFinalReview(JointActivityPreliminaryReview):
    final_score: int = Field(0, ge=0)


class JointActivityInfo(JointActivityBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    initiator_club_id: int
    created_by_user_id: int
    preliminary_status: AuditStatusEnum
    preliminary_auditor_id: int | None
    preliminary_reviewed_at: datetime | None
    archive_text: str | None
    archive_files: list[str]
    final_status: AuditStatusEnum | None
    final_score: int
    final_submitted_at: datetime | None
    final_auditor_id: int | None
    final_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    academic_term: AcademicTermInfo
    initiator_club: JointActivityClubInfo
    participations: list[JointActivityParticipationInfo]
