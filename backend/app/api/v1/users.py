from typing import Annotated

from fastapi import Depends, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import get_current_user, get_db
from app.schemas.user import UserInfo

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/me",
    response_model=UserInfo,
    status_code=status.HTTP_200_OK,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_current_user_info(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> UserInfo:
    return current_user
