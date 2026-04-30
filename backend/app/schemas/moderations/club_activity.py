from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generic import IdMixin


class ClubActivityCreateRequestInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: int = Field(...)

    name: str = Field(...)
    description: str = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    location: str = Field(...)


class ClubActivityCreateRequestCreatePublic(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    location: str = Field(...)


class ClubActivityCreateRequestCreate(ClubActivityCreateRequestCreatePublic):
    model_config = ConfigDict(from_attributes=True)

    club_id: int = Field(...)
    requestor_id: int = Field(...)
