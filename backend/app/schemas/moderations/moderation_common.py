from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.moderations.moderation_common import ModerateStatusEnum
from app.schemas.generic import IdMixin
from app.services.errors import BadRequestError, RequestIsNullError


class RequestModeratePublic(BaseModel):
    moderate_status: ModerateStatusEnum = Field(...)

    @model_validator(mode="after")
    def validate_moderate_status(self) -> RequestModeratePublic:
        if self.moderate_status not in {
            ModerateStatusEnum.approved,
            ModerateStatusEnum.rejected,
        }:
            raise BadRequestError(
                "error.request_moderate.invalid_moderate_status",
                "INVALID_MODERATE_STATUS",
            )
        return self


class RequestModerate(RequestModeratePublic):
    model_config = ConfigDict(from_attributes=True)

    moderator_id: int = Field(...)
    moderate_at: datetime = Field(...)


class RequestInfoBase(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    moderate_status: ModerateStatusEnum = Field(...)
    moderate_at: datetime | None = Field(None)

    requestor_id: int = Field(...)
    request_at: datetime = Field(...)


class UpdateRequestCreateBase(BaseModel):
    """Moderate Request 校验基类."""

    @model_validator(mode="after")
    def validate_any_payload_provided(self) -> Self:
        exclude_system_fields = {
            "moderator_id",
            "moderate_at",
            "requestor_id",
            "request_at",
            "user_id",
            "club_id",
            "club_activity_id",
        }

        valid_payload = self.model_dump(
            exclude_none=True,
            exclude=exclude_system_fields,
        )

        if not valid_payload:
            raise RequestIsNullError(
                "error.update_request.is_null",
                "UPDATE_REQUEST_IS_NULL",
            )

        return self
