from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserInfo, UserUpdate
from app.services.user import (
    get_user_by_email,
    get_user_by_user_id,
    update_user,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/me",
    response_model=UserInfo,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.get("/{user_id}", response_model=UserInfo)
async def get_user_profile(user_id: int, db: SessionDep) -> User:
    user = await get_user_by_user_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )
    return user


@router.patch(
    "/me",
    response_model=UserInfo,
    responses=TOKEN_INVALID_RESPONSE
    | {
        409: {
            "description": "Email already exists",
            "content": {
                "application/json": {"example": {"detail": "Email already exists"}},
            },
        },
    },
)
async def update_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: SessionDep,
    update: UserUpdate,
) -> User:
    if update.email:
        user = await get_user_by_email(db, update.email)
        if user is not None and user.id != current_user.id:
            raise HTTPException(status_code=409, detail="Email already exists")
    return await update_user(db, current_user, update)
