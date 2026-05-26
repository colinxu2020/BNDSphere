from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubActivityCreateRequestServiceDep,
    ClubActivityServiceDep,
    ClubActivityUpdateRequestServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
    get_current_user,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreate,
    ClubActivityCreateRequestCreatePublic,
    ClubActivityCreateRequestInfo,
    ClubActivityUpdateRequestCreate,
    ClubActivityUpdateRequestCreatePublic,
    ClubActivityUpdateRequestInfo,
)
from app.services.errors import (
    ClubActivityNotFoundError,
    ClubNotFoundError,
    DuplicatePendingRequestError,
    ResourceForbiddenError,
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
    club_service: ClubServiceDep,
) -> Page[ClubActivityInfo]:
    """List all activities of the given club."""
    club = await club_service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    return Page[ClubActivityInfo].model_validate(
        await service.get_club_activities(club),
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
    service: ClubActivityCreateRequestServiceDep,
    club_service: ClubServiceDep,
    requestor: Annotated[User, Depends(get_current_user)],
) -> ClubActivityCreateRequestInfo:
    """Create a new club activity request."""
    await club_service.ensure_club_normal(club_id)

    return ClubActivityCreateRequestInfo.model_validate(
        await service.create(
            ClubActivityCreateRequestCreate(
                **obj_in.model_dump(),
                club_id=club_id,
                requestor_id=requestor.id,
            ),
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
    service: ClubActivityUpdateRequestServiceDep,
    club_service: ClubServiceDep,
    club_activity_service: ClubActivityServiceDep,
    requestor: Annotated[User, Depends(get_current_user)],
) -> ClubActivityUpdateRequestInfo:
    """Request to update a club activity."""
    await club_service.ensure_club_normal(club_id)

    activity = await club_activity_service.get(activity_id)
    if activity is None:
        raise ClubActivityNotFoundError(activity_id) from None

    if activity.club_id != club_id:
        raise ResourceForbiddenError(
            "error.club_activity.wrong_belong",
            "CLUB_ACTIVITY_WRONG_BELONG",
        )

    try:
        await service.supersede_pending_requests_by_activity(activity_id)

        return ClubActivityUpdateRequestInfo.model_validate(
            await service.create(
                ClubActivityUpdateRequestCreate(
                    **obj_in.model_dump(),
                    club_activity_id=activity_id,
                    requestor_id=requestor.id,
                ),
            ),
        )
    except IntegrityError:
        raise DuplicatePendingRequestError from None
