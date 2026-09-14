from typing import Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.core import constants
from app.schemas.generic import ensure_non_nullable_fields_present
from app.schemas.moderations.moderation_common import (
    RequestInfoBase,
    UpdateRequestCreateBase,
)
from app.schemas.upload import LogoUri


class ClubUpdateRequestBase(BaseModel):
    # Leave these unbounded: this base is also inherited by
    # ``ClubUpdateRequestInfo``, the response model for the pending-list/create/
    # moderate endpoints. Capping here would make a legacy over-limit pending row
    # fail response validation (500) before a moderator could even reject it.
    # The caps belong on the create-only schema below.
    summary: str | None = Field(None)
    description: str | None = Field(None)
    logo_uri: HttpUrl | None = Field(None)


class ClubUpdateRequestInfo(RequestInfoBase, ClubUpdateRequestBase):
    club_id: int = Field(...)


class ClubUpdateRequestCreatePublic(ClubUpdateRequestBase, UpdateRequestCreateBase):
    # Length caps mirror ClubUpdate (the schema applied on approval) so a request
    # that passes creation can never fail re-validation when a moderator approves.
    summary: str | None = Field(None, max_length=constants.CLUB_MAX_SUMMARY_LENGTH)
    description: str | None = Field(
        None,
        max_length=constants.CLUB_MAX_DESCRIPTION_LENGTH,
    )
    # Overrides ClubUpdateRequestBase.logo_uri: reject a non-uploaded URL at
    # request time instead of only when a moderator later approves it.
    logo_uri: LogoUri = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(self, {"summary", "description"})
        return self


class ClubUpdateRequestCreate(ClubUpdateRequestCreatePublic):
    club_id: int = Field(...)
    requestor_id: int = Field(...)
    update_fields: list[str] = Field(default_factory=list)
