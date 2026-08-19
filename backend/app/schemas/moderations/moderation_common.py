from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.moderations.moderation_common import ModerationStatusEnum
from app.schemas.generic import IdMixin
from app.services.errors import BadRequestError, RequestIsNullError
from app.services.moderation_payload import requested_update_fields


class RequestModeratePublic(BaseModel):
    moderation_status: ModerationStatusEnum = Field(...)

    @model_validator(mode="after")
    def validate_moderation_status(self) -> RequestModeratePublic:
        if self.moderation_status not in {
            ModerationStatusEnum.approved,
            ModerationStatusEnum.rejected,
        }:
            raise BadRequestError(
                "error.request_moderate.invalid_moderation_status",
                "INVALID_MODERATION_STATUS",
            )
        return self


class RequestModerate(RequestModeratePublic):
    model_config = ConfigDict(from_attributes=True)

    moderator_id: int = Field(...)
    moderate_at: datetime = Field(...)


class RequestInfoBase(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderation_status: ModerationStatusEnum = Field(...)
    moderate_at: datetime | None = Field(None)

    requestor_id: int = Field(...)
    request_at: datetime = Field(...)


class UpdateRequestCreateBase(BaseModel):
    """Moderation Request 校验基类."""

    @model_validator(mode="after")
    def validate_any_payload_provided(self) -> Self:
        if not requested_update_fields(self):
            raise RequestIsNullError(
                "error.update_request.is_null",
                "UPDATE_REQUEST_IS_NULL",
            )

        return self


class ModerationPendingSummary(BaseModel):
    """Pending counts per moderation queue.

    Exists so the navigation rail can show a badge without fetching all four
    moderation lists. Deliberately narrow: counts the UI actually renders, nothing
    more. It is not a general statistics endpoint, and it does not change how any
    queue is read or moderated.
    """

    user_update_requests: int = Field(..., ge=0)
    club_update_requests: int = Field(..., ge=0)
    club_activity_create_requests: int = Field(..., ge=0)
    club_activity_update_requests: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
