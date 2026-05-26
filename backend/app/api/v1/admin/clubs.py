from fastapi import APIRouter
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import (
    ClubServiceDep,
)
from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.schemas.club import (
    AdminClubUpdate,
    ClubInfo,
)
from app.services.errors import ClubNotFoundError

router = APIRouter(tags=["Admin: Clubs"])


@router.get(
    "/",
)
async def list_clubs(
    service: ClubServiceDep,
    search: str | None = None,
    category: ClubCategoryEnum | None = None,
    club_status: ClubStatusEnum | None = None,
) -> Page[ClubInfo]:
    """Search Clubs. For admin."""
    return Page[ClubInfo].model_validate(
        await service.get_multi(search, category, club_status),
    )


@router.get(
    "/{club_id}",
)
async def get_club_info(club_id: int, service: ClubServiceDep) -> ClubInfo:
    """Get information of a club by club id. For admin."""
    club = await service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None

    return ClubInfo.model_validate(club)


@router.patch(
    "/{club_id}",
    response_model=ClubInfo,
    responses=RESOURCE_NOT_FOUND_RESPONSE,
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
