from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ActivityServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
)
from app.models.activity import Activity
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityInfo

router = APIRouter(tags=["club_activities"])
ClubRoleCheckerRequiresPresidentVice = Annotated[
    User,
    Depends(ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president])),
]


@router.get(
    "/",
    response_model=Page[ActivityInfo],
)
async def get_club_activities(
    club_id: int,
    offset: int,
    limit: int,
    service: ActivityServiceDep,
    club_service: ClubServiceDep,
) -> Page[Activity]:
    club = await club_service.get(club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found",
        )
    return await service.get_club_activities(club, offset, limit)


@router.post(
    "/",
    response_model=ActivityInfo,
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president]),
        ),
    ],
)
async def create_club_activity(
    club_id: int,
    activity: ActivityCreate,
    activity_service: ActivityServiceDep,
) -> Activity:
    return await activity_service.create(activity, club_id=club_id)
