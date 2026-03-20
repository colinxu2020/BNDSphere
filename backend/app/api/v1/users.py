from typing import Annotated

from fastapi import Depends, APIRouter, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.core.security import create_access_token
from app.schemas.user import UserInfo, UserCreate, Token
from app.services.user import get_user_by_username, create_user, authenticate

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

@router.post('/login', response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: SessionDep):
    user = await authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {'access_token': create_access_token({'sub': str(user.id)}), 'token_type':'bearer'}

