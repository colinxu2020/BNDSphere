from pydantic import BaseModel, Field, HttpUrl

from app.schemas.moderations.moderation_common import (
    RequestInfoBase,
    UpdateRequestCreateBase,
)


class ClubUpdateRequestBase(BaseModel):
    summary: str | None = Field(None)
    description: str | None = Field(None)
    logo_uri: HttpUrl | None = Field(None)


class ClubUpdateRequestInfo(RequestInfoBase, ClubUpdateRequestBase):
    club_id: int = Field(...)


class ClubUpdateRequestCreatePublic(ClubUpdateRequestBase, UpdateRequestCreateBase):
    pass


class ClubUpdateRequestCreate(ClubUpdateRequestCreatePublic):
    club_id: int = Field(...)
    requestor_id: int = Field(...)
