from fastapi import APIRouter

from app.api.dependencies import ClubServiceDep
from app.models.club import Club
from app.schemas.admin.club import AdminClubUpdate
from app.schemas.club import ClubInfo

router = APIRouter(tags=["clubs"])


@router.patch(
    "/{club_id}",
    response_model=ClubInfo,
)
async def update_club_info(
    club_id: int,
    obj_in: AdminClubUpdate,
    club_service: ClubServiceDep,
) -> Club:
    club = await club_service.ensure_club_normal(club_id)
    return await club_service.update(club, obj_in)
