from typing import Annotated

from pydantic import BaseModel, Field

from app.core import constants
from app.models.verification_code import VerificationChannelEnum

NewPassword = Annotated[
    str,
    Field(
        min_length=constants.USER_MIN_PASSWORD_LENGTH,
        max_length=constants.USER_MAX_PASSWORD_LENGTH,
    ),
]


class PasswordChange(BaseModel):
    # Bounded at the same ceiling as a new one: it is fed to the same argon2
    # verify, so leaving it open would only move the CPU-burning field.
    current_password: str = Field(
        ...,
        min_length=1,
        max_length=constants.USER_MAX_PASSWORD_LENGTH,
    )
    new_password: NewPassword


class PasswordResetTarget(BaseModel):
    username: str = Field(..., max_length=constants.USER_MAX_USERNAME_LENGTH)
    channel: VerificationChannelEnum


class PasswordResetRequest(PasswordResetTarget):
    # Carried in the body rather than as a form field: the rest of this
    # request is JSON, and FastAPI cannot read a ``Form`` alongside it.
    altcha: str = Field(
        ...,
        min_length=1,
        max_length=constants.ALTCHA_MAX_PAYLOAD_LENGTH,
    )


class PasswordResetConfirm(PasswordResetTarget):
    code: str = Field(
        ...,
        min_length=constants.VERIFICATION_CODE_DIGITS,
        max_length=constants.VERIFICATION_CODE_DIGITS,
    )
    new_password: NewPassword
