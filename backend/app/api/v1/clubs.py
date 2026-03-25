from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import get_current_user, get_db
from app.models.club import Club, ClubStatusEnum
from app.models.clubmember import ClubUserMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubInfo
from app.services.club import (
    get_club_by_club_id,
    get_clubs_by_club_name,
    set_club_relationship,
)

router = APIRouter(tags=["clubs"])
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{club_id}",
    response_model=ClubInfo,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_club_info(club_id: int, db: SessionDep) -> Club:
    """Get information of a club by club id."""
    club = await get_club_by_club_id(db, club_id)
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
    db: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Club:
    """Create a new club. Club name must be unique in active clubs."""
    existing_clubs = await get_clubs_by_club_name(db, club.name)
    for existing_club in existing_clubs:
        if existing_club.status == ClubStatusEnum.normal:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Club with name {club.name} already exists",
            )
    club = await create_club(club, db)
    await set_club_relationship(db, club, user, ClubUserMembershipEnum.president)
    return club
