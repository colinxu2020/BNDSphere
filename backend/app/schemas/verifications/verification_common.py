from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.verifications.verification_common import VerificationStatusEnum
from app.schemas.generic import IdMixin
from app.services.errors import BadRequestError


class RequestVerifyPublic(BaseModel):
    verification_status: VerificationStatusEnum = Field(...)

    @model_validator(mode="after")
    def validate_verification_status(self) -> RequestVerifyPublic:
        if self.verification_status not in {
            VerificationStatusEnum.approved,
            VerificationStatusEnum.rejected,
        }:
            raise BadRequestError(
                "error.request_verify.invalid_verification_status",
                "INVALID_VERIFICATION_STATUS",
            )
        return self


class RequestVerify(RequestVerifyPublic):
    model_config = ConfigDict(from_attributes=True)

    verifier_id: int = Field(...)
    verify_at: datetime = Field(...)


class VerificationInfoBase(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verification_status: VerificationStatusEnum = Field(...)
    verify_at: datetime | None = Field(None)

    applicant_id: int = Field(...)
    apply_at: datetime = Field(...)
