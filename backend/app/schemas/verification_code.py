from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.core import constants


class VerificationCodeCreate(BaseModel):
    user_id: int
    target: str
    code_hash: str
    expires_at: datetime


# Existing registration and login accept long passwords; reauthentication
# must accept those same credentials.
CurrentPassword = Annotated[
    str,
    Field(min_length=1),
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
