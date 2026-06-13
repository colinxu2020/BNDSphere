from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubActivityServiceDep,
    ClubRoleChecker,
    get_current_user,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreatePublic,
    ClubActivityCreateRequestInfo,
    ClubActivityUpdateRequestCreatePublic,
    ClubActivityUpdateRequestInfo,
)

router = APIRouter(tags=["Club Activities"])
ClubRoleCheckerRequiresPresidentVice = Annotated[
    User,
    Depends(
        ClubRoleChecker(
            [ClubMembershipEnum.vice_president, ClubMembershipEnum.president],
        ),
    ),
]


@router.get(
    "/",
)
async def get_club_activities(
    club_id: int,
    service: ClubActivityServiceDep,
) -> Page[ClubActivityInfo]:
    """List all activities of the given club."""
    return Page[ClubActivityInfo].model_validate(
        await service.get_club_activities_by_club_id(club_id),
    )


@router.post(
    "/create-requests",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker(
                [ClubMembershipEnum.president, ClubMembershipEnum.vice_president],
            ),
        ),
    ],
)
async def create_club_activity_request(
    club_id: int,
    obj_in: ClubActivityCreateRequestCreatePublic,
    service: ClubActivityServiceDep,
    requestor: Annotated[User, Depends(get_current_user)],
) -> ClubActivityCreateRequestInfo:
    """Create a new club activity request."""
    return ClubActivityCreateRequestInfo.model_validate(
        await service.request_club_activity_create(
            club_id,
            obj_in,
            requestor,
        ),
    )


@router.post(
    "/update-requests/{activity_id}",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker(
                [ClubMembershipEnum.president, ClubMembershipEnum.vice_president],
            ),
        ),
    ],
)
async def update_club_activity_request(
    club_id: int,
    activity_id: int,
    obj_in: ClubActivityUpdateRequestCreatePublic,
    service: ClubActivityServiceDep,
    requestor: Annotated[User, Depends(get_current_user)],
) -> ClubActivityUpdateRequestInfo:
    """Request to update a club activity."""
    return ClubActivityUpdateRequestInfo.model_validate(
        await service.request_club_activity_update(
            club_id,
            activity_id,
            obj_in,
            requestor,
        ),
    )
