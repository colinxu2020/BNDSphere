from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core import constants
from app.schemas.club_activity import ensure_activity_time_range
from app.schemas.generic import ensure_non_nullable_fields_present
from app.schemas.moderations.moderation_common import (
    RequestInfoBase,
    UpdateRequestCreateBase,
)


class ClubActivityCreateRequestBase(BaseModel):
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        ensure_activity_time_range(self.start_time, self.end_time)
        return self


class ClubActivityCreateRequestInfo(RequestInfoBase, ClubActivityCreateRequestBase):
    club_id: int = Field(...)


class ClubActivityCreateRequestCreatePublic(ClubActivityCreateRequestBase):
    pass


class ClubActivityCreateRequestCreate(ClubActivityCreateRequestCreatePublic):
    model_config = ConfigDict(from_attributes=True)

    club_id: int = Field(...)
    requestor_id: int = Field(...)


class ClubActivityUpdateRequestBase(BaseModel):
    name: str | None = Field(None, max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str | None = Field(
        None,
        max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH,
    )
    start_time: datetime | None = Field(None)
    end_time: datetime | None = Field(None)
    location: str | None = Field(
        None,
        max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH,
    )
    picture_urls: list[str] | None = Field(None)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.start_time is not None and self.end_time is not None:
            ensure_activity_time_range(self.start_time, self.end_time)
        return self


class ClubActivityUpdateRequestInfo(RequestInfoBase, ClubActivityUpdateRequestBase):
    club_activity_id: int = Field(...)


class ClubActivityUpdateRequestCreatePublic(
    ClubActivityUpdateRequestBase,
    UpdateRequestCreateBase,
):
    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(
            self,
            {
                "name",
                "description",
                "start_time",
                "end_time",
                "location",
                "picture_urls",
            },
        )
        return self


class ClubActivityUpdateRequestCreate(ClubActivityUpdateRequestCreatePublic):
    model_config = ConfigDict(from_attributes=True)

    club_activity_id: int = Field(...)
    requestor_id: int = Field(...)
    update_fields: list[str] = Field(default_factory=list)
