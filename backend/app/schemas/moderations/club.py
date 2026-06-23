from typing import Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas.generic import ensure_non_nullable_fields_present
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
    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(self, {"summary", "description"})
        return self


class ClubUpdateRequestCreate(ClubUpdateRequestCreatePublic):
    club_id: int = Field(...)
    requestor_id: int = Field(...)
    update_fields: list[str] = Field(default_factory=list)
