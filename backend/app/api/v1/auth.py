from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import AuthServiceDep, UserServiceDep
from app.api.rate_limit import client_ip, login_rate_limit, register_rate_limit
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserInfo
from app.services.errors import AuthenticationError

router = APIRouter(tags=["Auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
    responses={
        409: {
            "description": "Username already exists",
            "content": {
                "application/json": {"example": {"detail": "Username already exists"}},
            },
        },
    },
)
async def register(user: UserCreate, service: UserServiceDep) -> UserInfo:
    """Register a new user. Username must be unique."""
    return UserInfo.model_validate(await service.create(user))


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(login_rate_limit)],
    responses={
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
    request: Request,
) -> Token:
    """Login with username and password. Returns a JWT token if successful.

    Note that all optional fields in the form data are ignored.
    """
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
