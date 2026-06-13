from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.dependencies import (
    ClubUpdateRequestServiceDep,
    get_current_user,
)
from app.models import User
from app.schemas.moderations.club import ClubUpdateRequestInfo
from app.schemas.moderations.moderation_common import RequestModeratePublic

router = APIRouter(tags=["Moderation: Clubs"])


@router.get(
    "/update-requests",
)
async def get_pending_update_request(
    service: ClubUpdateRequestServiceDep,
) -> Page[ClubUpdateRequestInfo]:
    """Get pending club update request."""
    return Page[ClubUpdateRequestInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch(
    "/update-requests/{request_id}",
)
async def moderate_update_request(
    request_id: int,
    obj_in: RequestModeratePublic,
    service: ClubUpdateRequestServiceDep,
    moderator: Annotated[User, Depends(get_current_user)],
) -> ClubUpdateRequestInfo:
    """Moderate club update request."""
    return ClubUpdateRequestInfo.model_validate(
        await service.approve_club_update_request(request_id, obj_in, moderator),
    )
