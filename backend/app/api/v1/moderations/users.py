from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.dependencies import (
    UserUpdateRequestServiceDep,
    get_current_user,
)
from app.models.user import User
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestInfo,
)

router = APIRouter(tags=["Moderation: Users"])


@router.get(
    "/update-requests",
)
async def get_user_profile_update_requests(
    service: UserUpdateRequestServiceDep,
) -> Page[UserUpdateRequestInfo]:
    """Get all pending user profile update requests."""
    return Page[UserUpdateRequestInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch(
    "/update-requests/{request_id}",
)
async def moderate_user_profile_update_request(
    request_id: int,
    obj_in: RequestModeratePublic,
    service: UserUpdateRequestServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> UserUpdateRequestInfo:
    return UserUpdateRequestInfo.model_validate(
        await service.approve_user_update_request(request_id, obj_in, user),
    )
