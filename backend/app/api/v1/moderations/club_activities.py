from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ActivityServiceDep,
    ClubActivityCreateRequestServiceDep,
    ClubServiceDep,
    get_current_user,
)
from app.models.moderations.moderation_common import ModerateStatusEnum
from app.models.user import User
from app.schemas.activity import ActivityCreate
from app.schemas.moderations.club_activity import ClubActivityCreateRequestInfo
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.services.errors import (
    ClubNotFoundError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)

router = APIRouter(tags=["Club Activities"])


@router.get(
    "/create-request",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def get_pending_create_request(
    service: ClubActivityCreateRequestServiceDep,
) -> Page[ClubActivityCreateRequestInfo]:
    """Get pending club activity create request."""
    return Page[ClubActivityCreateRequestInfo].model_validate(
        await service.get_pending_request(),
    )


@router.patch(
    "/create-request/{request_id}",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
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
    request = await service.get(request_id)
    if request is None:
        raise ResourceNotFoundError(
            "error.club_activity_create_request.not_found",
            "CLUB_ACTIVITY_CREATE_REQUEST_NOT_FOUND",
        )
    if request.moderate_status != ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.club_activity_create_request.moderated",
            "CLUB_ACTIVITY_CREATE_REQUEST_MODERATED",
        )

    club = await club_service.get(request.club_id)
    if club is None:
        raise ClubNotFoundError(request.club_id)

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        await club_activity_service.create_club_activity(
            club.id,
            ActivityCreate(
                name=request.name,
                description=request.description,
                start_time=request.start_time,
                end_time=request.end_time,
                location=request.location,
            ),
        )

    return ClubActivityCreateRequestInfo.model_validate(
        await service.moderate_request(request, obj_in, moderator),
    )
