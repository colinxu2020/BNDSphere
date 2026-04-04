from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import ServiceFactory, get_current_user
from app.models.user import User
from app.schemas.user import UserInfo, UserUpdate
from app.services.errors import DuplicateEmailError
from app.services.user import UserService

router = APIRouter(tags=["users"])
ServiceDep = Annotated[UserService, Depends(ServiceFactory(UserService))]


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
async def get_user_profile(user_id: int, service: ServiceDep) -> User:
    """Get public profile of a user by user id."""
    user = await service.get(user_id)
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
    service: ServiceDep,
    update: UserUpdate,
) -> User:
    """Modify user profile of current user.

    Note that username cannot be changed, and email must be unique.
    """
    try:
        return await service.update(current_user, update)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already exists") from None
