from typing import Annotated, cast

from fastapi import Depends, status, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserInfo
from app.services.user import get_user_by_username, get_user_by_user_id

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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found."
        )
    return user
