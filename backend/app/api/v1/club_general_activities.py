from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    ClubGeneralActivityServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityInfo,
)

router = APIRouter(tags=["club_general_activities"])
ClubRoleCheckerRequiresPresidentVice = Annotated[
    User,
    Depends(ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president])),
]


@router.get("/")
async def get_club_general_activities(
    club_id: int,
    club_service: ClubServiceDep,
    club_general_activity_service: ClubGeneralActivityServiceDep,
) -> list[ClubGeneralActivityInfo]:
    club = await club_service.ensure_club_normal(club_id)
    return [
        ClubGeneralActivityInfo.model_validate(c)
        for c in await club_general_activity_service.get_by_club(club)
    ]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president]),
        ),
    ],
)
async def create_club_general_activities(
    club_id: int,
    obj: ClubGeneralActivityCreate,
    club_service: ClubServiceDep,
    club_general_activity_service: ClubGeneralActivityServiceDep,
) -> ClubGeneralActivityInfo:
    club = await club_service.ensure_club_normal(club_id)
    return await club_general_activity_service.create_club_general_activity(
        obj,
        club.id,
    )
