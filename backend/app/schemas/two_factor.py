from enum import StrEnum

from pydantic import BaseModel, Field

from app.core import constants


class TwoFactorMethodEnum(StrEnum):
    """What can answer a second-factor challenge."""

    totp = "totp"
    sms = "sms"
    recovery = "recovery"


class RecoveryCodeCreate(BaseModel):
    user_id: int
    code_hash: str


class TwoFactorStatus(BaseModel):
    totp_enabled: bool
    sms_enabled: bool
    # Whether SMS *could* be turned on — there is a verified number to send to.
    sms_available: bool
    recovery_codes_remaining: int


class TotpEnrollment(BaseModel):
    """The shared secret, the only time the server hands it back.

    Both forms of the same thing: the URI for a QR code or a deep link, and
    the bare secret for typing into an app that will not scan.
    """

    secret: str
    provisioning_uri: str


class RecoveryCodes(BaseModel):
    """Shown once. The server keeps only hashes, so it cannot show them again."""

    recovery_codes: list[str]


class _Password(BaseModel):
    """Re-authentication for a change to how the account is protected.

    A live session is not enough: these routes decide whether a stolen session
    can quietly remove the thing standing in its way.
    """

    password: str = Field(
        ...,
        min_length=1,
        max_length=constants.USER_MAX_PASSWORD_LENGTH,
    )


class TwoFactorPasswordConfirm(_Password):
    pass


class TotpConfirm(BaseModel):
    code: str = Field(
        ...,
        min_length=constants.VERIFICATION_CODE_DIGITS,
        max_length=constants.VERIFICATION_CODE_DIGITS,
    )


class TwoFactorChallenge(BaseModel):
    """The ticket handed out when a correct password is not yet a login."""

    two_factor_token: str = Field(..., min_length=1, max_length=2048)


class TwoFactorSubmit(TwoFactorChallenge):
    method: TwoFactorMethodEnum
    # Wide enough for a recovery code; the six-digit methods are length-checked
    # where they are verified, so one field covers all three.
    code: str = Field(
        ...,
        min_length=constants.VERIFICATION_CODE_DIGITS,
        max_length=constants.RECOVERY_CODE_MAX_INPUT_LENGTH,
    )
