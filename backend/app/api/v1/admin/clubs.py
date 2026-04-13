from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.dependencies import (
    ClubServiceDep,
    ClubUpdateRequestServiceDep,
    get_current_user,
)
from app.models.club import Club
from app.models.user import User
from app.schemas.club import (
    AdminClubUpdate,
    ClubInfo,
    ClubUpdateRequestAudit,
    ClubUpdateRequestInfo,
)
from app.services.errors import ClubNotFoundError

router = APIRouter(tags=["clubs"])


@router.patch(
    "/{club_id}",
    response_model=ClubInfo,
)
async def admin_update_club_info(
    club_id: int,
    obj_in: AdminClubUpdate,
    club_service: ClubServiceDep,
) -> Club:
    """Update the information of a club."""
    club = await club_service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    return await club_service.update(club, obj_in)


@router.get(
    "/update-requests",
)
async def list_pending_update_requests(
    update_request_service: ClubUpdateRequestServiceDep,
) -> Page[ClubUpdateRequestInfo]:
    """List all pending club update requests for admin review."""
    return Page[ClubUpdateRequestInfo].model_validate(
        await update_request_service.get_pending_requests(),
    )


@router.patch(
    "/update-requests/{request_id}",
)
async def audit_update_request(
    request_id: int,
    audit_in: ClubUpdateRequestAudit,
    club_service: ClubServiceDep,
    update_request_service: ClubUpdateRequestServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubUpdateRequestInfo:
    """Approve or reject a club update request.

    If approved, the club info will be updated with the requested changes.
    """
    request = await update_request_service.ensure_request(request_id)
    club = await club_service.get(request.club_id)
    if club is None:
        raise ClubNotFoundError(request.club_id) from None
    result = await update_request_service.audit(
        request,
        audit_in.audit_status,
        user,
        club,
    )
    return ClubUpdateRequestInfo.model_validate(result)
