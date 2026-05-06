from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.moderations.moderation_common import (
    RequestInfoBase,
    UpdateRequestCreateBase,
)


class ClubActivityCreateRequestBase(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    location: str = Field(...)


class ClubActivityCreateRequestInfo(RequestInfoBase, ClubActivityCreateRequestBase):
    club_id: int = Field(...)


class ClubActivityCreateRequestCreatePublic(ClubActivityCreateRequestBase):
    pass


class ClubActivityCreateRequestCreate(ClubActivityCreateRequestCreatePublic):
    model_config = ConfigDict(from_attributes=True)

    club_id: int = Field(...)
    requestor_id: int = Field(...)


class ClubActivityUpdateRequestBase(BaseModel):
    name: str | None = Field(None)
    description: str | None = Field(None)
    start_time: datetime | None = Field(None)
    end_time: datetime | None = Field(None)
    location: str | None = Field(None)


class ClubActivityUpdateRequestInfo(RequestInfoBase, ClubActivityUpdateRequestBase):
    club_activity_id: int = Field(...)


class ClubActivityUpdateRequestCreatePublic(
    ClubActivityUpdateRequestBase,
    UpdateRequestCreateBase,
):
    pass


class ClubActivityUpdateRequestCreate(ClubActivityUpdateRequestCreatePublic):
    model_config = ConfigDict(from_attributes=True)

    club_activity_id: int = Field(...)
    requestor_id: int = Field(...)
