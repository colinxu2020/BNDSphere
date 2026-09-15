from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.common_responses import ALTCHA_VERIFICATION_FAILED_RESPONSE
from app.api.dependencies import AltchaServiceDep, AuthServiceDep, UserServiceDep
from app.api.rate_limit import (
    challenge_rate_limit,
    client_ip,
    login_rate_limit,
    register_rate_limit,
)
from app.core import constants
from app.core.security import create_access_token
from app.schemas.altcha import AltchaChallenge, AltchaPurpose
from app.schemas.user import Token, UserInfo, UserRegistration
from app.services.errors import AuthenticationError

router = APIRouter(tags=["Auth"])


@router.get(
    "/altcha/challenge",
    response_model=AltchaChallenge,
    dependencies=[Depends(challenge_rate_limit)],
)
def get_altcha_challenge(
    purpose: AltchaPurpose,
    response: Response,
    altcha_service: AltchaServiceDep,
) -> AltchaChallenge:
    """Create a short-lived, single-use ALTCHA Core challenge."""
    response.headers["Cache-Control"] = "no-store"
    return AltchaChallenge.model_validate(
        altcha_service.create_challenge(purpose).to_dict(),
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
    responses=ALTCHA_VERIFICATION_FAILED_RESPONSE
    | {
        409: {
            "description": "Username already exists",
            "content": {
                "application/json": {"example": {"detail": "Username already exists"}},
            },
        },
    },
)
async def register(
    user: UserRegistration,
    service: UserServiceDep,
    altcha_service: AltchaServiceDep,
) -> UserInfo:
    """Register a new user after all legal consents are explicitly accepted.

    Username must be unique.
    """
    altcha_service.verify(user.altcha, AltchaPurpose.register)
    return UserInfo.model_validate(await service.create(user))


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(login_rate_limit)],
    responses=ALTCHA_VERIFICATION_FAILED_RESPONSE
    | {
        401: {
            "description": "Incorrect username or password",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect username or password"},
                },
            },
        },
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
    altcha_service: AltchaServiceDep,
    request: Request,
    altcha: Annotated[
        str,
        Form(min_length=1, max_length=constants.ALTCHA_MAX_PAYLOAD_LENGTH),
    ],
) -> Token:
    """Login with username and password. Returns a JWT token if successful.

    Note that all optional fields in the form data are ignored.
    """
    altcha_service.verify(altcha, AltchaPurpose.login)
    user = await service.authenticate(
        form_data.username,
        form_data.password,
        ip=client_ip(request),
    )
    if not user:
        raise AuthenticationError(
            "error.auth.incorrect_user_passwd",
            "INCORRECT_USER_PASSWD",
        )
    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        token_type="bearer",  # noqa: S106
    )
