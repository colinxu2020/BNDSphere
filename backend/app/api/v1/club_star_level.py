from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubRoleChecker,
    ClubServiceDep,
    StarLevelServiceDep,
)
from app.models.clubmember import ClubMembershipEnum
from app.schemas.star_level import StarLevelApplicationCreate, StarLevelApplicationInfo
from app.services.errors import ClubNotFoundError

router = APIRouter(tags=["Club Star Level"])


@router.get(
    "/",
)
async def get_club_applications(
    club_id: int,
    service: StarLevelServiceDep,
    club_service: ClubServiceDep,
) -> Page[StarLevelApplicationInfo]:
    """List all star level applications of the given club."""
    club = await club_service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    return Page[StarLevelApplicationInfo].model_validate(
        await service.list_by_club(club),
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.president]),
        ),
    ],
)
async def create_club_star_level_application(
    club_id: int,
    request: StarLevelApplicationCreate,
    service: StarLevelServiceDep,
) -> StarLevelApplicationInfo:
    """Create a new star level application for the given club."""
    return StarLevelApplicationInfo.model_validate(
        await service.create(request, club_id=club_id),
    )
