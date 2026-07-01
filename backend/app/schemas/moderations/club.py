from typing import Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas.generic import ensure_non_nullable_fields_present
from app.schemas.moderations.moderation_common import (
    RequestInfoBase,
    UpdateRequestCreateBase,
)
from app.schemas.upload import LogoUri


class ClubUpdateRequestBase(BaseModel):
    summary: str | None = Field(None)
    description: str | None = Field(None)
    logo_uri: HttpUrl | None = Field(None)


class ClubUpdateRequestInfo(RequestInfoBase, ClubUpdateRequestBase):
    club_id: int = Field(...)


class ClubUpdateRequestCreatePublic(ClubUpdateRequestBase, UpdateRequestCreateBase):
    # Overrides ClubUpdateRequestBase.logo_uri: reject a non-uploaded URL at
    # request time instead of only when a moderator later approves it.
    logo_uri: LogoUri = Field(None)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(self, {"summary", "description"})
        return self


class ClubUpdateRequestCreate(ClubUpdateRequestCreatePublic):
    club_id: int = Field(...)
    requestor_id: int = Field(...)
    update_fields: list[str] = Field(default_factory=list)
