from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import (
    ClubServiceDep,
    get_current_user,
)
from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.user import User
from app.schemas.club import (
    AdminClubCreate,
    AdminClubUpdate,
    ClubInfo,
)
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicateResourceError,
)

router = APIRouter(tags=["Admin: Clubs"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Club with the same name already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Club with name HCC already exists."},
                },
            },
        },
    },
)
async def create_club(
    club: AdminClubCreate,
    service: ClubServiceDep,
    admin: Annotated[User, Depends(get_current_user)],
) -> ClubInfo:
    """Create an active club with an optional historical creation time."""
    try:
        club_created = await service.create_club(
            club,
            admin,
            status=ClubStatusEnum.normal,
        )
    except DuplicateClubNameError:
        raise DuplicateResourceError(
            message_key="error.club.duplicate_club_name",
            error_code="DUPLICATE_CLUB_NAME",
        ) from None
    return ClubInfo.model_validate(club_created)


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
    responses=RESOURCE_NOT_FOUND_RESPONSE,
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
