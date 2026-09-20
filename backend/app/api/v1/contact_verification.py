from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.common_responses import (
    CONTACT_VERIFICATION_SEND_RESPONSES,
    TOKEN_INVALID_RESPONSE,
    VERIFICATION_CODE_INVALID_RESPONSE,
)
from app.api.dependencies import ContactVerificationServiceDep, get_current_user
from app.models.user import User
from app.schemas.user import UserInfo
from app.schemas.verification_code import (
    EmailVerificationConfirm,
    EmailVerificationSend,
    PhoneVerificationConfirm,
    PhoneVerificationSend,
    VerificationCodeSent,
)

router = APIRouter(tags=["Verification"])


@router.post(
    "/email/send",
    status_code=status.HTTP_202_ACCEPTED,
    responses=TOKEN_INVALID_RESPONSE | CONTACT_VERIFICATION_SEND_RESPONSES,
)
async def send_email_code(
    body: EmailVerificationSend,
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> VerificationCodeSent:
    """Send a verification code to an email address for the current account.

    202, not 200: the provider accepting the message is not delivery, and the
    response says nothing about whether it arrived.
    """
    return await service.send_email_code(user, body.email)


@router.post(
    "/email/confirm",
    responses=TOKEN_INVALID_RESPONSE | VERIFICATION_CODE_INVALID_RESPONSE,
)
async def confirm_email_code(
    body: EmailVerificationConfirm,
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """Answer an emailed code and bind the address to the current account."""
    return UserInfo.model_validate(
        await service.confirm_email_code(user, body.email, body.code),
    )


@router.post(
    "/phone/send",
    status_code=status.HTTP_202_ACCEPTED,
    responses=TOKEN_INVALID_RESPONSE | CONTACT_VERIFICATION_SEND_RESPONSES,
)
async def send_phone_code(
    body: PhoneVerificationSend,
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> VerificationCodeSent:
    """Send a verification code by SMS for the current account."""
    return await service.send_phone_code(user, body.phone)


@router.post(
    "/phone/confirm",
    responses=TOKEN_INVALID_RESPONSE | VERIFICATION_CODE_INVALID_RESPONSE,
)
async def confirm_phone_code(
    body: PhoneVerificationConfirm,
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """Answer an SMS code and bind the number to the current account."""
    return UserInfo.model_validate(
        await service.confirm_phone_code(user, body.phone, body.code),
    )
