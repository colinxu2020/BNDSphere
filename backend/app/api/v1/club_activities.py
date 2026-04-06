from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import ServiceFactory, get_current_user
from app.models.activity import Activity
from app.models.club import ClubStatusEnum
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
    club_service: ClubServiceDep,
) -> PageResponse[ActivityInfo]:
    club = await club_service.get(club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found",
        )
    result = await service.get_club_activities(club, offset, limit)
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
    club_id: int,
    activity: ActivityCreate,
    activity_service: ActivityServiceDep,
    club_service: ClubServiceDep,
    membership_service: MemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Activity:
    try:
        club = await club_service.get(club_id)

        if club is None or club.status != ClubStatusEnum.normal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found or status valid",
            ) from None
        if not await membership_service.is_club_admin(club, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
            ) from None

        return await activity_service.create_club_activity(club_id, activity)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected error",
        ) from None
