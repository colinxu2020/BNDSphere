from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.dependencies import (
    UserServiceDep,
    UserUpdateRequestServiceDep,
    get_current_user,
)
from app.models.moderations.moderation_common import ModerateStatusEnum
from app.models.user import User
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestInfo,
)
from app.schemas.user import AdminUserUpdate
from app.services.errors import (
    ResourceForbiddenError,
    ResourceNotFoundError,
    UserNotFoundError,
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
    user_service: UserServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> UserUpdateRequestInfo:
    request = await service.get_with_lock(request_id)
    if request is None:
        raise ResourceNotFoundError(
            "error.user_update_request.not_found",
            "USER_UPDATE_REQUEST_NOT_FOUND",
        ) from None
    if request.moderate_status != ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.user_update_request.moderated",
            "USER_UPDATE_REQUEST_MODERATED",
        ) from None

    request_user = await user_service.get(request.user_id)
    if request_user is None:
        raise UserNotFoundError(request.user_id) from None

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        await user_service.update(
            request_user,
            AdminUserUpdate.model_validate(request),
        )

    return UserUpdateRequestInfo.model_validate(
        await service.moderate_request(request, obj_in, user),
    )
