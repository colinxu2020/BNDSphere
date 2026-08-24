from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.common_responses import (
    DUPLICATE_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    TOKEN_INVALID_RESPONSE,
)
from app.api.dependencies import (
    UserServiceDep,
    UserUpdateRequestServiceDep,
    get_current_user,
)
from app.models.user import User
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestCreate,
    UserUpdateRequestInfo,
)
from app.schemas.user import PublicUserInfo, UserInfo
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["Users"])


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
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def get_user_profile(user_id: int, service: UserServiceDep) -> PublicUserInfo:
    """Get public profile of a user by user id."""
    user = await service.get(user_id)
    if user is None:
        raise ResourceNotFoundError(
            message_key="error.user.not_found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id},
        ) from None
    return PublicUserInfo.model_validate(user)


@router.post(
    "/update-requests",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | DUPLICATE_REQUEST_RESPONSE,
)
async def request_update_profile(
    service: UserUpdateRequestServiceDep,
    obj_in: UserUpdateRequestCreate,
    user: Annotated[User, Depends(get_current_user)],
) -> UserUpdateRequestInfo:
    """Request update user profile of current user."""
    return UserUpdateRequestInfo.model_validate(
        await service.request_profile_update(obj_in, user),
    )
