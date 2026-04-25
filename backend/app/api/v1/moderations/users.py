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
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestInfo,
    UserUpdateRequestModerate,
    UserUpdateRequestModeratePublic,
)
from app.schemas.user import AdminUserUpdate
from app.services.errors import ResourceForbiddenError, ResourceNotFoundError

router = APIRouter(tags=["users"])


@router.get("/profile-update")
async def get_user_profile_update_requests(
    service: UserUpdateRequestServiceDep,
) -> Page[UserUpdateRequestInfo]:
    """Get all pending user profile update requests."""
    return Page[UserUpdateRequestInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch("/profile-update/{request_id}")
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
        )
    if request.moderate_status is not ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.user_update_request.moderate_approved",
            "USER_UPDATE_REQUEST_MODERATE_APPROVED",
        )
    ret = await service.update(
        request,
        UserUpdateRequestModerate(
            **obj_in.model_dump(),
            moderator_id=user.id,
        ),
    )

    dct = {}
    if ret.username:
        dct["username"] = ret.username
    if ret.avatar_uri:
        dct["avatar_uri"] = ret.avatar_uri
    if ret.description:
        dct["description"] = ret.description

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        request_user = await user_service.get(ret.user_id)
        if request_user is None:
            raise ResourceNotFoundError(
                "error.user.not_found",
                "USER_NOT_FOUND",
            )
        await user_service.update(request_user, AdminUserUpdate.model_validate(dct))

    return UserUpdateRequestInfo.model_validate(ret)
