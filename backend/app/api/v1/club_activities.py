from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import ServiceFactory, get_current_user
from app.models.activity import Activity
from app.models.club import ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityInfo
from app.schemas.generic import PageResponse
from app.services.activity import ActivityService
from app.services.club import ClubMemberService, ClubService

router = APIRouter(tags=["club_activities"])
ActivityServiceDep = Annotated[
    ActivityService,
    Depends(ServiceFactory(ActivityService)),
]
ClubServiceDep = Annotated[ClubService, Depends(ServiceFactory(ClubService))]
MemberServiceDep = Annotated[
    ClubMemberService,
    Depends(ServiceFactory(ClubMemberService)),
]


@router.get(
    "/",
)
async def get_club_activities(
    club_id: int,
    offset: int,
    limit: int,
    service: ActivityServiceDep,
) -> PageResponse[ActivityInfo]:
    result = await service.get_club_activities(club_id, offset, limit)
    return PageResponse(
        total=result.total,
        items=[ActivityInfo.model_validate(c) for c in result.items],
    )


@router.post(
    "/",
    response_model=ActivityInfo,
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE,
)
async def create_club_activity(
    activity: ActivityCreate,
    activity_service: ActivityServiceDep,
    club_service: ClubServiceDep,
    membership_service: MemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Activity:
    try:
        club = await club_service.get(activity.club_id)
        if club is None or club.status != ClubStatusEnum.normal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found or status valid",
            ) from None
        membership = await membership_service.get_by_club_user(club, user)
        if not membership or membership not in {
            ClubMembershipEnum.president,
            ClubMembershipEnum.vice,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
            ) from None
        return await activity_service.create(activity)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected error",
        ) from None
