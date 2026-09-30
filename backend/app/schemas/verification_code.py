from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.core import constants
from app.models.verification_code import (
    VerificationChannelEnum,
    VerificationPurposeEnum,
)


class VerificationCodeCreate(BaseModel):
    user_id: int
    channel: VerificationChannelEnum
    purpose: VerificationPurposeEnum
    target: str
    code_hash: str
    expires_at: datetime


# Bounded at the same ceiling as the password itself: it is fed to the same
# argon2 verify, so leaving it open would only move the CPU-burning field.
CurrentPassword = Annotated[
    str,
    Field(min_length=1, max_length=constants.USER_MAX_PASSWORD_LENGTH),
]
VerificationCodeDigits = Annotated[
    str,
    Field(
        min_length=constants.VERIFICATION_CODE_DIGITS,
        max_length=constants.VERIFICATION_CODE_DIGITS,
    ),
]


class EmailVerificationTarget(BaseModel):
    email: EmailStr = Field(..., max_length=constants.USER_MAX_EMAIL_LENGTH)


class EmailVerificationSend(EmailVerificationTarget):
    # Only on the send step. Answering the code needs no password because no
    # code exists to answer until one was sent with it.
    password: CurrentPassword


class EmailVerificationConfirm(EmailVerificationTarget):
    code: VerificationCodeDigits


class PhoneVerificationTarget(BaseModel):
    # Validated and normalized to E.164 by ``normalize_phone``; kept a plain
    # string here so the user sees one domain-specific error message instead
    # of a pydantic pattern dump.
    phone: str = Field(..., max_length=constants.USER_MAX_PHONE_INPUT_LENGTH)


class PhoneVerificationSend(PhoneVerificationTarget):
    password: CurrentPassword


class PhoneVerificationConfirm(PhoneVerificationTarget):
    code: VerificationCodeDigits


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
