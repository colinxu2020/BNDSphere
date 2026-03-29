from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import ServiceFactory, get_current_user
from app.models.club import Club, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubInfo
from app.services.club import ClubMemberService, ClubService

router = APIRouter(tags=["clubs"])
ServiceDep = Annotated[ClubService, Depends(ServiceFactory(ClubService))]
MemberServiceDep = Annotated[
    ClubMemberService,
    Depends(ServiceFactory(ClubMemberService)),
]


@router.get(
    "/{club_id}",
    response_model=ClubInfo,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_club_info(club_id: int, service: ServiceDep) -> Club:
    """Get information of a club by club id."""
    club = await service.get(club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Club with id {club_id} not found",
        )
    return club


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
    service: ServiceDep,
    membership_service: MemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Club:
    """Create a new club. Club name must be unique in active clubs."""
    existing_clubs = await service.get_by_name(club.name)
    for existing_club in existing_clubs:
        if existing_club.status in {ClubStatusEnum.normal, ClubStatusEnum.unreviewed}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Club with name {club.name} already exists",
            )
    club = await service.create(club)
    await membership_service.set_relationship(club, user, ClubMembershipEnum.president)
    return club
