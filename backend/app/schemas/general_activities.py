from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core import constants
from app.models.general_activity import (
    AuditStatusEnum,
    GeneralActivityLevelEnum,
    ParticipationTypeEnum,
)
from app.schemas.generic import IdMixin


class GeneralActivityBase(BaseModel):
    name: str = Field(..., max_length=constants.GENERAL_ACTIVITY_MAX_NAME_LENGTH)
    description: str
    level: GeneralActivityLevelEnum


class GeneralActivityCreate(GeneralActivityBase):
    pass


class GeneralActivityInfo(GeneralActivityBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    club_records: list[ClubGeneralActivityInfo]


class GeneralActivityUpdate(BaseModel):
    name: str | None = Field(
        None,
        max_length=constants.GENERAL_ACTIVITY_MAX_NAME_LENGTH,
    )
    description: str | None = Field(None)
    level: GeneralActivityLevelEnum | None = Field(None)


class ClubGeneralActivityBase(BaseModel):
    proof_files: str | None
    created_at: datetime
    audit_status: AuditStatusEnum
    requested_score: int
    participation_type: ParticipationTypeEnum
    met_conditions: list[RecordConditionDetail]


class ClubGeneralActivityInfo(ClubGeneralActivityBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    final_score: int
    club_id: int
    activity_id: int


class ClubGeneralActivityCreate(ClubGeneralActivityBase):
    pass


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
