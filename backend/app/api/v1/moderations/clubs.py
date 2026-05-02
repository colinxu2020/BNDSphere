from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubServiceDep,
    ClubUpdateRequestServiceDep,
    get_current_user,
)
from app.models import User
from app.models.club import ClubStatusEnum
from app.models.moderations.moderation_common import ModerateStatusEnum
from app.schemas.club import AdminClubUpdate
from app.schemas.moderations.club import ClubUpdateRequestInfo
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.services.errors import (
    ClubNotFoundError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)

router = APIRouter(tags=["clubs"])


@router.get(
    "/update-request",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def get_pending_update_request(
    service: ClubUpdateRequestServiceDep,
) -> Page[ClubUpdateRequestInfo]:
    """Get pending club update request."""
    return Page[ClubUpdateRequestInfo].model_validate(
        await service.get_pending_request(),
    )


@router.patch(
    "/update-request/{request_id}",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def moderate_update_request(
    request_id: int,
    obj_in: RequestModeratePublic,
    service: ClubUpdateRequestServiceDep,
    club_service: ClubServiceDep,
    moderator: Annotated[User, Depends(get_current_user)],
) -> ClubUpdateRequestInfo:
    """Moderate club update request."""
    request = await service.get(request_id)
    if request is None:
        raise ResourceNotFoundError(
            "error.club_update_request.not_found",
            "CLUB_UPDATE_REQUEST_NOT_FOUND",
        ) from None
    if request.moderate_status != ModerateStatusEnum.pending:
        raise ResourceForbiddenError(
            "error.club_update_request.moderated",
            "CLUB_UPDATE_REQUEST_MODERATED",
        ) from None

    club = await club_service.get(request.club_id)
    if club is None or club.status != ClubStatusEnum.normal:
        raise ClubNotFoundError(request.club_id) from None

    if obj_in.moderate_status == ModerateStatusEnum.approved:
        update_data_dict = {
            k: getattr(request, k)
            for k in [
                "summary",
                "description",
                "logo_uri",
            ]
            if getattr(request, k) is not None
        }
        await club_service.update(
            club,
            AdminClubUpdate.model_validate(update_data_dict),
        )

    return ClubUpdateRequestInfo.model_validate(
        await service.moderate_request(request, obj_in, moderator),
    )
