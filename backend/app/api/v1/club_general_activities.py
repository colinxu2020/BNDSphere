from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubGeneralActivityServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
    GeneralActivityServiceDep,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import AuditStatusEnum
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityInfo,
    ClubGeneralActivityUpdate,
)
from app.services.errors import (
    GeneralActivityNotFoundError,
    ResourceForbiddenError,
)

router = APIRouter(tags=["Club General Activities"])


@router.get("/")
async def get_club_general_activities(
    club_id: int,
    club_service: ClubServiceDep,
    club_general_activity_service: ClubGeneralActivityServiceDep,
) -> Page[ClubGeneralActivityInfo]:
    club = await club_service.ensure_club_normal(club_id)
    return Page[ClubGeneralActivityInfo].model_validate(
        await club_general_activity_service.get_by_club(club),
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president]),
        ),
    ],
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def create_club_general_activities(
    club_id: int,
    obj: ClubGeneralActivityCreate,
    club_service: ClubServiceDep,
    general_activity_service: ClubGeneralActivityServiceDep,
    club_general_activity_service: ClubGeneralActivityServiceDep,
) -> ClubGeneralActivityInfo:
    club = await club_service.ensure_club_normal(club_id)
    activity = await general_activity_service.get(obj.activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(obj.activity_id) from None

    return ClubGeneralActivityInfo.model_validate(
        await club_general_activity_service.create_club_general_activity(
            obj,
            club.id,
        ),
    )


@router.patch(
    "/",
    dependencies=[
        Depends(
            ClubRoleChecker([ClubMembershipEnum.vice, ClubMembershipEnum.president]),
        ),
    ],
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def update_club_general_activities(
    club_id: int,
    obj: ClubGeneralActivityUpdate,
    club_service: ClubServiceDep,
    general_activity_service: GeneralActivityServiceDep,
    club_general_activity_service: ClubGeneralActivityServiceDep,
) -> ClubGeneralActivityInfo:
    club = await club_service.ensure_club_normal(club_id)
    activity = await general_activity_service.get(obj.activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(obj.activity_id) from None
    record = await club_general_activity_service.get_by_club_activity(club, activity)
    if record.audit_status != AuditStatusEnum.pending:
        raise ResourceForbiddenError(
            message_key="error.general_activity.record_reviewed",
            error_code="RECORD_REVIEWED",
            details={
                "club_id": club_id,
                "activity_id": activity.id,
            },
        ) from None

    return ClubGeneralActivityInfo.model_validate(
        await club_general_activity_service.update(record, obj),
    )
