from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.common_responses import ALTCHA_VERIFICATION_FAILED_RESPONSE
from app.api.dependencies import (
    AltchaServiceDep,
    AuthServiceDep,
    UserServiceDep,
    UserSessionServiceDep,
    session_token,
)
from app.api.rate_limit import (
    challenge_rate_limit,
    client_ip,
    login_rate_limit,
    register_rate_limit,
)
from app.core import constants
from app.core.settings import web_settings
from app.schemas.altcha import AltchaChallenge, AltchaPurpose
from app.schemas.user import Token, UserInfo, UserRegistration
from app.services.errors import AuthenticationError

router = APIRouter(tags=["Auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    """Hand the session token to the browser as a cookie.

    ``HttpOnly`` keeps it out of reach of page scripts, which is the point of
    moving off the previous ``localStorage`` token: an XSS can no longer read
    the credential and walk away with a week of access.

    ``SameSite=Lax`` is the CSRF defence. Every state-changing route here is
    POST/PUT/PATCH/DELETE, and Lax withholds the cookie from cross-site
    requests with those methods; it is only sent on top-level GET navigations,
    which change nothing.

    ``Secure`` is dropped in debug so local development over plain HTTP still
    works; production runs behind Caddy over TLS and sets it.
    """
    response.set_cookie(
        constants.SESSION_COOKIE_NAME,
        token,
        max_age=constants.SESSION_LIFETIME_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=not web_settings().debug,
        samesite="lax",
        path="/",
    )


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
    session_service: UserSessionServiceDep,
    altcha_service: AltchaServiceDep,
    request: Request,
    response: Response,
    altcha: Annotated[
        str,
        Form(min_length=1, max_length=constants.ALTCHA_MAX_PAYLOAD_LENGTH),
    ],
) -> Token:
    """Login with username and password. Opens a session if successful.

    The session token is returned two ways for one credential: as an
    ``HttpOnly`` cookie, which is what the web app uses and never exposes to
    page scripts, and in the response body, which keeps ``/api/docs`` and
    non-browser clients working. Browser callers should ignore the body.

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
    token = await session_service.issue(user)
    _set_session_cookie(response, token)
    return Token(
        access_token=token,
        token_type="bearer",  # noqa: S106
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session_service: UserSessionServiceDep,
    token: Annotated[str | None, Depends(session_token)],
) -> None:
    """End the current session and clear the cookie.

    Deliberately unauthenticated and idempotent: a caller whose session has
    already expired or been revoked still wants the cookie gone, and making
    them authenticate first would turn signing out into an error.
    """
    if token:
        await session_service.revoke(token)
    # The attributes must match the ones the cookie was set with, or the
    # browser treats this as a different cookie and leaves the original.
    response.delete_cookie(
        constants.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=not web_settings().debug,
        samesite="lax",
    )
