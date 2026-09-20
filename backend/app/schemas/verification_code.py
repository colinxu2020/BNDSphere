from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core import constants
from app.models.verification_code import VerificationChannelEnum


class VerificationCodeCreate(BaseModel):
    user_id: int
    channel: VerificationChannelEnum
    target: str
    code_hash: str
    expires_at: datetime


class EmailVerificationSend(BaseModel):
    email: EmailStr = Field(..., max_length=constants.USER_MAX_EMAIL_LENGTH)


class EmailVerificationConfirm(EmailVerificationSend):
    code: str = Field(
        ...,
        min_length=constants.VERIFICATION_CODE_DIGITS,
        max_length=constants.VERIFICATION_CODE_DIGITS,
    )


class PhoneVerificationSend(BaseModel):
    # Validated and normalized to E.164 by ``normalize_phone``; kept a plain
    # string here so the user sees one domain-specific error message instead
    # of a pydantic pattern dump.
    phone: str = Field(..., max_length=constants.USER_MAX_PHONE_INPUT_LENGTH)


class PhoneVerificationConfirm(PhoneVerificationSend):
    code: str = Field(
        ...,
        min_length=constants.VERIFICATION_CODE_DIGITS,
        max_length=constants.VERIFICATION_CODE_DIGITS,
    )


class VerificationCodeSent(BaseModel):
    """What the client needs to drive the "enter the code" screen.

    Carries no hint about whether the code was actually delivered: a bad
    address or a dead handset is not something the send path can observe, and
    reporting the provider's acceptance as delivery would be a lie.
    """

    expires_in: int = Field(..., description="Seconds until the code expires.")
    resend_after: int = Field(
        ...,
        description="Seconds until another code may be requested.",
    )
