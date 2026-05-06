from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    UserServiceDep,
    UserUpdateRequestServiceDep,
    get_current_user,
)
from app.models.user import User
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestInfo,
    UserUpdateUpdateRequestCreate,
)
from app.schemas.user import UserInfo
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """Get public profile of current user."""
    return UserInfo.model_validate(current_user)


@router.get(
    "/{user_id}",
)
async def get_user_profile(user_id: int, service: UserServiceDep) -> UserInfo:
    """Get public profile of a user by user id."""
    user = await service.get(user_id)
    if user is None:
        raise ResourceNotFoundError(
            message_key="error.user.not_found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id},
        ) from None
    return UserInfo.model_validate(user)


@router.post(
    "/update-requests",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE,
)
async def request_update_profile(
    service: UserUpdateRequestServiceDep,
    obj_in: UserUpdateUpdateRequestCreate,
    user: Annotated[User, Depends(get_current_user)],
) -> UserUpdateRequestInfo:
    """Request update user profile of current user."""
    await service.supersede_pending_requests_by_user(user.id)

    return UserUpdateRequestInfo.model_validate(
        await service.create(obj_in, user_id=user.id),
    )
