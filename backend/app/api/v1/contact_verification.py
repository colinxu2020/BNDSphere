from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.common_responses import (
    CONTACT_POLICY_CHANGED_RESPONSE,
    CONTACT_POLICY_REQUIRED_RESPONSE,
    CONTACT_VERIFICATION_SEND_RESPONSES,
    PASSWORD_REQUIRED_RESPONSE,
    TOKEN_INVALID_RESPONSE,
    VERIFICATION_CODE_INVALID_RESPONSE,
)
from app.api.dependencies import ContactVerificationServiceDep, get_current_user
from app.api.rate_limit import client_ip
from app.models.user import User
from app.schemas.contact_policy import ContactPolicyAcceptance, ContactPolicyStatus
from app.schemas.user import UserInfo
from app.schemas.verification_code import (
    EmailVerificationConfirm,
    EmailVerificationSend,
    VerificationCodeSent,
)

router = APIRouter(tags=["Verification"])


@router.get("/contact-policy", responses=TOKEN_INVALID_RESPONSE)
async def contact_policy_status(
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ContactPolicyStatus:
    return await service.contact_policy_status(user)


@router.post(
    "/contact-policy",
    responses=TOKEN_INVALID_RESPONSE | CONTACT_POLICY_CHANGED_RESPONSE,
)
async def accept_contact_policy(
    body: ContactPolicyAcceptance,
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ContactPolicyStatus:
    """Record explicit acceptance of the version shown before contact binding."""
    return await service.accept_contact_policy(user, body.version)


@router.post(
    "/email/send",
    status_code=status.HTTP_202_ACCEPTED,
    responses=TOKEN_INVALID_RESPONSE
    | PASSWORD_REQUIRED_RESPONSE
    | CONTACT_VERIFICATION_SEND_RESPONSES
    | CONTACT_POLICY_REQUIRED_RESPONSE,
)
async def send_email_code(
    body: EmailVerificationSend,
    service: ContactVerificationServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> VerificationCodeSent:
    """Send a verification code to an email address for the current account.

    The account password is required: this address becomes where password
    resets are delivered, so a live session alone must not be able to move it.

    202, not 200: the provider accepting the message is not delivery, and the
    response says nothing about whether it arrived.
    """
    return await service.send_email_code(
        user,
        body.email,
        body.password,
        ip=client_ip(request),
    )


@router.post(
    "/email/confirm",
    responses=TOKEN_INVALID_RESPONSE
    | VERIFICATION_CODE_INVALID_RESPONSE
    | CONTACT_POLICY_REQUIRED_RESPONSE,
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
