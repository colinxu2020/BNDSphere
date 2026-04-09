from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubMemberServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
    get_current_user,
)
from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubInfo, ClubMemberInfo, ClubUpdate
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicateResourceError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)

router = APIRouter(tags=["clubs"])


@router.get(
    "/{club_id}",
    response_model=ClubInfo,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_club_info(club_id: int, service: ClubServiceDep) -> Club:
    """Get information of a club by club id."""
    return await service.ensure_club_normal(club_id)


@router.post(
    "/",
    response_model=ClubInfo,
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE
    | {
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
    club: ClubCreate,
    service: ClubServiceDep,
    membership_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Club:
    """Create a new club. Club name must be unique among non-archived clubs."""
    try:
        club = await service.create(club)
    except DuplicateClubNameError:
        raise DuplicateResourceError(
            message_key="error.club.duplicate_club_name",
            error_code="DUPLICAE_CLUB_NAME",
        ) from None
    await membership_service.set_relationship(club, user, ClubMembershipEnum.president)
    return club


@router.patch(
    "/{club_id}",
    response_model=ClubInfo,
    responses=TOKEN_INVALID_RESPONSE,
    dependencies=[Depends(ClubRoleChecker([ClubMembershipEnum.president]))],
)
async def update_club_info(
    club_id: int,
    club_update: ClubUpdate,
    service: ClubServiceDep,
) -> Club:
    """Get information of a club by club id."""
    club = await service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    return await service.update(club, club_update)


@router.get(
    "/",
    response_model=Page[ClubInfo],
)
async def list_clubs(
    service: ClubServiceDep,
    search: str | None = None,
    category: ClubCategoryEnum | None = None,
    status: ClubStatusEnum | None = None,
) -> Page[Club]:
    """Search Clubs."""
    return await service.get_multi(search, category, status)


@router.post(
    "/{club_id}/members",
    response_model=ClubMemberInfo,
    status_code=status.HTTP_201_CREATED,
)
async def join_club(
    club_id: int,
    service: ClubServiceDep,
    membership_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubMemberInfo:
    """Join a club."""
    club = await service.ensure_club_normal(club_id)
    relationship = await membership_service.get_by_club_user(club, user)
    if relationship and relationship.membership != ClubMembershipEnum.left:
        raise DuplicateResourceError(
            message_key="error.club.duplicate_join_request",
            error_code="DUPLICAE_JOIN_REQUEST",
        ) from None
    return await membership_service.set_relationship(
        club,
        user,
        ClubMembershipEnum.pending,
    )


@router.delete(
    "/{club_id}/members/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def leave_club(
    club_id: int,
    service: ClubServiceDep,
    membership_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Leave a club."""
    club = await service.ensure_club_normal(club_id)

    relationship = await membership_service.get_by_club_user(club, user)
    if relationship is None or relationship == ClubMembershipEnum.left:
        raise ResourceNotFoundError(
            message_key="error.club.is_not_member",
            error_code="IS_NOT_MEMBER",
        ) from None
    if relationship.membership in {
        ClubMembershipEnum.vice,
        ClubMembershipEnum.president,
    }:
        raise ResourceForbiddenError(
            message_key="error.club.not_allowed_leave",
            error_code="NOT_ALLOWED_LEAVE_CLUB",
        ) from None

    await membership_service.set_relationship(
        club,
        user,
        ClubMembershipEnum.left,
    )
