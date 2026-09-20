from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.common_responses import (
    ALTCHA_VERIFICATION_FAILED_RESPONSE,
    CONTACT_VERIFICATION_SEND_RESPONSES,
    PASSWORD_RESET_CODE_INVALID_RESPONSE,
    TOKEN_INVALID_RESPONSE,
    TWO_FACTOR_LOGIN_RESPONSES,
)
from app.api.dependencies import (
    AltchaServiceDep,
    AuthServiceDep,
    PasswordServiceDep,
    TwoFactorServiceDep,
    UserServiceDep,
    UserSessionServiceDep,
    get_current_user,
    session_token,
)
from app.api.rate_limit import (
    challenge_rate_limit,
    client_ip,
    login_rate_limit,
    password_reset_rate_limit,
    register_rate_limit,
)
from app.core import constants
from app.core.settings import web_settings
from app.models.user import User
from app.schemas.altcha import AltchaChallenge, AltchaPurpose
from app.schemas.password import (
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
)
from app.schemas.two_factor import TwoFactorChallenge, TwoFactorSubmit
from app.schemas.user import Token, UserInfo, UserRegistration
from app.schemas.verification_code import VerificationCodeSent
from app.services.errors import AuthenticationError, TwoFactorRequiredError

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
    two_factor_service: TwoFactorServiceDep,
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

    An account with a second factor gets no session here: the response is
    401 ``TWO_FACTOR_REQUIRED`` carrying a short-lived challenge ticket and
    the list of methods that can answer it, and ``/auth/login/2fa`` is what
    finishes the login.

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
    if user.two_factor_enabled:
        raise TwoFactorRequiredError(
            two_factor_service.begin_challenge(user),
            [method.value for method in two_factor_service.methods_for(user)],
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


@router.post(
    "/password/change",
    response_model=Token,
    responses=TOKEN_INVALID_RESPONSE,
)
async def change_password(
    body: PasswordChange,
    service: PasswordServiceDep,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
    response: Response,
) -> Token:
    """Change the current account's password, re-checking the old one.

    Every session is ended and a new one opened for this caller, so the
    change signs out every other device — which is the reason most people
    change a password in the first place. The cookie is replaced in the same
    response, so this device stays signed in.
    """
    token = await service.change(
        user,
        body.current_password,
        body.new_password,
        ip=client_ip(request),
    )
    _set_session_cookie(response, token)
    return Token(
        access_token=token,
        token_type="bearer",  # noqa: S106
    )


@router.post(
    "/password/reset/request",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(password_reset_rate_limit)],
    responses=ALTCHA_VERIFICATION_FAILED_RESPONSE
    | {429: CONTACT_VERIFICATION_SEND_RESPONSES[429]},
)
async def request_password_reset(
    body: PasswordResetRequest,
    service: PasswordServiceDep,
    altcha_service: AltchaServiceDep,
) -> VerificationCodeSent:
    """Send a reset code to a verified address on the named account.

    Always answers 202 with the same body, whether or not the account exists
    and whether or not it has anything verified on that channel: this route
    is unauthenticated, and any observable difference would turn it into a
    username oracle. The 429 it can still return comes from the per-IP
    budget, which does not depend on the account named.
    """
    altcha_service.verify(body.altcha, AltchaPurpose.password_reset)
    return await service.request_reset(body.username, body.channel)


@router.post(
    "/password/reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(password_reset_rate_limit)],
    responses=PASSWORD_RESET_CODE_INVALID_RESPONSE,
)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    service: PasswordServiceDep,
) -> None:
    """Answer a reset code and set a new password.

    Ends every session on the account and opens none: whoever answered the
    code has to log in with the new password, so a code that leaked is not by
    itself a way in.
    """
    await service.confirm_reset(
        body.username,
        body.channel,
        body.code,
        body.new_password,
    )


@router.post(
    "/login/2fa/send",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(login_rate_limit)],
    responses=TWO_FACTOR_LOGIN_RESPONSES
    | {429: CONTACT_VERIFICATION_SEND_RESPONSES[429]},
)
async def send_two_factor_login_code(
    body: TwoFactorChallenge,
    two_factor_service: TwoFactorServiceDep,
) -> VerificationCodeSent:
    """Text a second-factor code to the account the challenge names.

    Unauthenticated by necessity — the caller is mid-login — but the ticket
    is only issued after a correct password, so this cannot be used to make a
    stranger's phone buzz.
    """
    return await two_factor_service.send_login_code(body.two_factor_token)


@router.post(
    "/login/2fa",
    response_model=Token,
    dependencies=[Depends(login_rate_limit)],
    responses=TWO_FACTOR_LOGIN_RESPONSES,
)
async def complete_two_factor_login(
    body: TwoFactorSubmit,
    two_factor_service: TwoFactorServiceDep,
    session_service: UserSessionServiceDep,
    request: Request,
    response: Response,
) -> Token:
    """Answer the second factor and open the session.

    No ALTCHA: the proof of work was already spent on the password step, and
    asking again would mean a caller whose challenge is about to expire has to
    solve one before they can use it.
    """
    user = await two_factor_service.complete_challenge(
        body.two_factor_token,
        body.method,
        body.code,
        ip=client_ip(request),
    )
    token = await session_service.issue(user)
    _set_session_cookie(response, token)
    return Token(
        access_token=token,
        token_type="bearer",  # noqa: S106
    )
