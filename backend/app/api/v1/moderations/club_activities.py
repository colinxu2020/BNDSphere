from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubActivityCreateRequestServiceDep,
    ClubActivityUpdateRequestServiceDep,
    get_current_user,
)
from app.models.user import User
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestInfo,
    ClubActivityUpdateRequestInfo,
)
from app.schemas.moderations.moderation_common import RequestModeratePublic

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
    moderator: Annotated[User, Depends(get_current_user)],
) -> ClubActivityCreateRequestInfo:
    """Moderate club activity create request."""
    return ClubActivityCreateRequestInfo.model_validate(
        await service.approve_club_activity_create_request(
            request_id,
            obj_in,
            moderator,
        ),
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
    moderator: Annotated[User, Depends(get_current_user)],
) -> ClubActivityUpdateRequestInfo:
    """Moderate club activity update request."""
    return ClubActivityUpdateRequestInfo.model_validate(
        await service.approve_club_activity_update_request(
            request_id,
            obj_in,
            moderator,
        ),
    )
