from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import UserServiceDep, get_current_user
from app.models.user import User
from app.schemas.user import UserInfo, UserUpdate
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    response_model=UserInfo,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get public profile of current user."""
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserInfo,
)
async def get_user_profile(user_id: int, service: UserServiceDep) -> User:
    """Get public profile of a user by user id."""
    user = await service.get(user_id)
    if user is None:
        raise ResourceNotFoundError(
            message_key="error.user.not_found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id},
        ) from None
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
    service: UserServiceDep,
    update: UserUpdate,
) -> User:
    """Modify user profile of current user.

    Note that username cannot be changed, and email must be unique.
    """
    return await service.update(current_user, update)
