from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from app.api.dependencies import UserServiceDep
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserInfo
from app.services.errors import AuthenticationError

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
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
    service: UserServiceDep,
) -> Token:
    """Login with username and password. Returns a JWT token if successful.

    Note that all optional fields in the form data are ignored.
    """
    user = await service.authenticate(form_data.username, form_data.password)
    if not user:
        raise AuthenticationError(
            "error.auth.incorrect_user_passwd",
            "INCORRECT_USER_PASSWD",
        )
    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        token_type="bearer",  # noqa: S106
    )
