from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    UserServiceDep,
    UserUpdateRequestServiceDep,
    get_current_user,
)
from app.models.moderations.moderation_common import ModerateStatusEnum
from app.models.user import User
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestInfo,
    UserUpdateRequestModeratePublic,
)
from app.schemas.user import AdminUserUpdate
from app.services.errors import (
    ResourceForbiddenError,
    ResourceNotFoundError,
    UserNotFoundError,
)

router = APIRouter(tags=["users"])


@router.get(
    "/profile-update",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def get_user_profile_update_requests(
    service: UserUpdateRequestServiceDep,
) -> Page[UserUpdateRequestInfo]:
    """Get all pending user profile update requests."""
    return Page[UserUpdateRequestInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch(
    "/profile-update/{request_id}",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def moderate_user_profile_update_request(
    request_id: int,
    obj_in: UserUpdateRequestModeratePublic,
    service: UserUpdateRequestServiceDep,
    user_service: UserServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> UserUpdateRequestInfo:
    request = await service.get(request_id)
    if request is None:
        raise ResourceNotFoundError(
            "error.user_update_request.not_found",
            "USER_UPDATE_REQUEST_NOT_FOUND",
        ) from None
    if request.moderate_status is not ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.user_update_request.moderated",
            "USER_UPDATE_REQUEST_MODERATED",
        ) from None

    request_user = await user_service.get(request.user_id)
    if request_user is None:
        raise UserNotFoundError(request.user_id) from None

    ret, dct = await service.moderate_request(request, obj_in, user)

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        await user_service.update(request_user, AdminUserUpdate.model_validate(dct))

    return UserUpdateRequestInfo.model_validate(ret)
