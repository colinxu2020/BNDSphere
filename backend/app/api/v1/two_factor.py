from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.common_responses import PASSWORD_REQUIRED_RESPONSE
from app.api.dependencies import TwoFactorServiceDep, get_current_user
from app.api.rate_limit import client_ip, login_rate_limit
from app.models.user import User
from app.schemas.two_factor import (
    RecoveryCodes,
    TotpConfirm,
    TotpEnrollment,
    TwoFactorPasswordConfirm,
    TwoFactorStatus,
)

router = APIRouter(tags=["Two-factor"])


@router.get("")
async def get_two_factor_status(
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> TwoFactorStatus:
    """Report what is armed on this account and how many recovery codes are left."""
    return await service.status(user)


@router.post(
    "/totp/start",
    dependencies=[Depends(login_rate_limit)],
    responses=PASSWORD_REQUIRED_RESPONSE,
)
async def start_totp_enrollment(
    body: TwoFactorPasswordConfirm,
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> TotpEnrollment:
    """Mint a TOTP secret for an authenticator app.

    Nothing is armed yet: the secret is stored unconfirmed, and it only starts
    being demanded at login once an app has answered a code from it.
    """
    return await service.start_totp(user, body.password, ip=client_ip(request))


@router.post("/totp/confirm", dependencies=[Depends(login_rate_limit)])
async def confirm_totp_enrollment(
    body: TotpConfirm,
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> RecoveryCodes:
    """Answer a code from the new secret and arm TOTP.

    Returns a set of recovery codes, shown once — but only if the account had
    none left. An account that already printed a set keeps it and gets an
    empty list back: replacing it is what ``/recovery-codes`` is for.
    """
    return await service.confirm_totp(user, body.code, ip=client_ip(request))


@router.post(
    "/totp/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(login_rate_limit)],
    responses=PASSWORD_REQUIRED_RESPONSE,
)
async def disable_totp(
    body: TwoFactorPasswordConfirm,
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> None:
    """Disarm TOTP and forget the secret."""
    await service.disable_totp(user, body.password, ip=client_ip(request))


@router.post(
    "/sms/enable",
    dependencies=[Depends(login_rate_limit)],
    responses=PASSWORD_REQUIRED_RESPONSE,
)
async def enable_sms_two_factor(
    body: TwoFactorPasswordConfirm,
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> RecoveryCodes:
    """Arm the account's verified number as a second factor."""
    return await service.enable_sms(user, body.password, ip=client_ip(request))


@router.post(
    "/sms/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(login_rate_limit)],
    responses=PASSWORD_REQUIRED_RESPONSE,
)
async def disable_sms_two_factor(
    body: TwoFactorPasswordConfirm,
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> None:
    await service.disable_sms(user, body.password, ip=client_ip(request))


@router.post(
    "/recovery-codes",
    dependencies=[Depends(login_rate_limit)],
    responses=PASSWORD_REQUIRED_RESPONSE,
)
async def regenerate_recovery_codes(
    body: TwoFactorPasswordConfirm,
    service: TwoFactorServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> RecoveryCodes:
    """Replace the recovery codes, invalidating the old set."""
    return await service.regenerate_recovery_codes(
        user,
        body.password,
        ip=client_ip(request),
    )
