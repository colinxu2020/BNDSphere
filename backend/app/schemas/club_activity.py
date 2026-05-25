from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core import constants
from app.schemas.academic_terms import AcademicTermInfo
from app.schemas.generic import IdMixin


class ClubActivityBase(BaseModel):
    name: str = Field(..., max_length=constants.ACTIVITY_MAX_NAME_LENGTH)
    description: str = Field(..., max_length=constants.ACTIVITY_MAX_DESCRIPTION_LENGTH)
    location: str = Field(..., max_length=constants.ACTIVITY_MAX_LOCATION_LENGTH)
    start_time: datetime
    end_time: datetime


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
