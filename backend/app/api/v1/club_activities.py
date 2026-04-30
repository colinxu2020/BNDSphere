from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ActivityServiceDep,
    ClubActivityCreateRequestServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
    get_current_user,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityInfo
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreate,
    ClubActivityCreateRequestCreatePublic,
    ClubActivityCreateRequestInfo,
)
from app.services.errors import ClubNotFoundError

router = APIRouter(tags=["Club Activities"])
ClubRoleCheckerRequiresPresidentVice = Annotated[
    User,
    Depends(ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president])),
]


@router.get(
    "/",
)
async def get_club_activities(
    club_id: int,
    service: ActivityServiceDep,
    club_service: ClubServiceDep,
) -> Page[ActivityInfo]:
    """List all activities of the given club."""
    club = await club_service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    return Page[ActivityInfo].model_validate(await service.get_club_activities(club))


@router.post(
    "/",
    response_model=ActivityInfo,
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president]),
        ),
    ],
    deprecated=True,
)
async def create_club_activity(
    club_id: int,
    activity: ActivityCreate,
    activity_service: ActivityServiceDep,
) -> ActivityInfo:
    """Create a new activity for the given club.
    Only club president and vice president can perform this operation.
    """
    return ActivityInfo.model_validate(
        await activity_service.create(activity, club_id=club_id),
    )


@router.post(
    "/create-request",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.president, ClubMembershipEnum.vice]),
        ),
    ],
)
async def create_club_activity_request(
    club_id: int,
    obj_in: ClubActivityCreateRequestCreatePublic,
    service: ClubActivityCreateRequestServiceDep,
    requestor: Annotated[User, Depends(get_current_user)],
) -> ClubActivityCreateRequestInfo:
    """Create a new club activity request."""
    return ClubActivityCreateRequestInfo.model_validate(
        await service.create(
            ClubActivityCreateRequestCreate(
                **obj_in.model_dump(),
                club_id=club_id,
                requestor_id=requestor.id,
            ),
        ),
    )
