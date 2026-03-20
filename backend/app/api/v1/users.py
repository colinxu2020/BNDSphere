from typing import Annotated

from fastapi import Depends, APIRouter, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.schemas.user import UserInfo, UserCreate
from app.services.user import get_user_by_username, create_user

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db)]

@router.post('/register', response_model = UserInfo, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: SessionDep) -> UserInfo:
    if await get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    return await create_user(db, user)

@router.post('/me', response_model=UserInfo, status_code=status.HTTP_200_OK)
async def get_current_user_info(current_user: Annotated[UserCreate, Depends(get_current_user)]) -> UserInfo:
    return current_user
