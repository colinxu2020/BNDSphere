from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core import constants
from app.schemas.academic_terms import AcademicTermInfo
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present
from app.services.errors import BadRequestError


def ensure_activity_time_range(start_time: datetime, end_time: datetime) -> None:
    if end_time <= start_time:
        raise BadRequestError(
            "error.club_activity.invalid_time_range",
            "CLUB_ACTIVITY_INVALID_TIME_RANGE",
        )


class ClubActivityBase(BaseModel):
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        ensure_activity_time_range(self.start_time, self.end_time)
        return self


class ClubActivityInfo(ClubActivityBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    club_id: int
    picture_urls: list[str]
    academic_term: AcademicTermInfo


class ClubActivityCreate(ClubActivityBase):
    pass


class ClubActivityUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = Field(None, max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str | None = Field(
        None,
        max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH,
    )
    location: str | None = Field(
        None,
        max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH,
    )
    start_time: datetime | None = Field(None)
    end_time: datetime | None = Field(None)
    picture_urls: list[str] | None = Field(None)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        ensure_non_nullable_fields_present(
            self,
            {
                "name",
                "description",
                "location",
                "start_time",
                "end_time",
                "picture_urls",
            },
        )
        if self.start_time is not None and self.end_time is not None:
            ensure_activity_time_range(self.start_time, self.end_time)
        return self
