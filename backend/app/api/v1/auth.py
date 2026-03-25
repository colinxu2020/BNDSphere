from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.dependencies import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserInfo
from app.services.user import authenticate, create_user, get_user_by_username

router = APIRouter(tags=["auth"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/register",
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "Username already exists",
            "content": {
                "application/json": {"example": {"detail": "Username already exists"}},
            },
        },
    },
)
async def register(user: UserCreate, db: SessionDep) -> User:
    """Register a new user. Username must be unique."""
    if await get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    return await create_user(db, user)


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
    db: SessionDep,
) -> Token:
    """Login with username and password. Returns a JWT token if successful.

    Note that all optional fields in the form data are ignored.
    """
    user = await authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        token_type="bearer",  # noqa: S106
    )
