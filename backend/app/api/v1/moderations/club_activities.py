from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ActivityServiceDep,
    ClubActivityCreateRequestServiceDep,
    ClubActivityUpdateRequestServiceDep,
    ClubServiceDep,
    get_current_user,
)
from app.models.moderations.moderation_common import ModerateStatusEnum
from app.models.user import User
from app.schemas.club_activity import ClubActivityCreate, ClubActivityUpdate
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestInfo,
    ClubActivityUpdateRequestInfo,
)
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.services.errors import (
    ClubActivityNotFoundError,
    ClubNotFoundError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)

router = APIRouter(tags=["Moderation: Club Activities"])


@router.get(
    "/create-requests",
)
async def get_pending_create_request(
    service: ClubActivityCreateRequestServiceDep,
) -> Page[ClubActivityCreateRequestInfo]:
    """Get pending club activity create request."""
    return Page[ClubActivityCreateRequestInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch(
    "/create-requests/{request_id}",
)
async def moderate_create_request(
    request_id: int,
    obj_in: RequestModeratePublic,
    service: ClubActivityCreateRequestServiceDep,
    club_service: ClubServiceDep,
    club_activity_service: ActivityServiceDep,
    moderator: Annotated[User, Depends(get_current_user)],
) -> ClubActivityCreateRequestInfo:
    """Moderate club activity create request."""
    request = await service.get_with_lock(request_id)
    if request is None:
        raise ResourceNotFoundError(
            "error.club_activity_create_request.not_found",
            "CLUB_ACTIVITY_CREATE_REQUEST_NOT_FOUND",
        ) from None
    if request.moderate_status != ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.club_activity_create_request.moderated",
            "CLUB_ACTIVITY_CREATE_REQUEST_MODERATED",
        ) from None

    club = await club_service.get(request.club_id)
    if club is None:
        raise ClubNotFoundError(request.club_id) from None

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        data_dict = {
            k: getattr(request, k)
            for k in ClubActivityCreate.model_fields
            if hasattr(request, k) and getattr(request, k) is not None
        }

        await club_activity_service.create_club_activity(
            club.id,
            ClubActivityCreate.model_validate(data_dict),
        )

    return ClubActivityCreateRequestInfo.model_validate(
        await service.moderate_request(request, obj_in, moderator),
    )


@router.get(
    "/update-requests",
)
async def get_pending_update_request(
    service: ClubActivityUpdateRequestServiceDep,
) -> Page[ClubActivityUpdateRequestInfo]:
    """Get pending club activity update request."""
    return Page[ClubActivityUpdateRequestInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch(
    "/update-requests/{request_id}",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def moderate_update_request(
    request_id: int,
    obj_in: RequestModeratePublic,
    service: ClubActivityUpdateRequestServiceDep,
    club_activity_service: ActivityServiceDep,
    moderator: Annotated[User, Depends(get_current_user)],
) -> ClubActivityUpdateRequestInfo:
    """Moderate club activity update request."""
    request = await service.get_with_lock(request_id)
    if request is None:
        raise ResourceNotFoundError(
            "error.club_activity_update_request.not_found",
            "CLUB_ACTIVITY_UPDATE_REQUEST_NOT_FOUND",
        ) from None
    if request.moderate_status != ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.club_activity_update_request.moderated",
            "CLUB_ACTIVITY_UPDATE_REQUEST_MODERATED",
        ) from None

    activity = await club_activity_service.get(request.club_activity_id)
    if activity is None:
        raise ClubActivityNotFoundError(request.club_activity_id) from None

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        await club_activity_service.update(
            activity,
            ClubActivityUpdate.model_validate(request),
        )

    return ClubActivityUpdateRequestInfo.model_validate(
        await service.moderate_request(request, obj_in, moderator),
    )
