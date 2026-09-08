from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubActivityCheckInServiceDep,
    ClubActivityServiceDep,
    ClubRoleChecker,
    get_current_user,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club_activity import ClubActivityInfo
from app.schemas.club_activity_check_in import (
    ClubActivityCheckInInfo,
    ClubActivityCheckInQrTokenInfo,
    ClubActivityManualCheckInRequest,
    ClubActivityQrCheckInRequest,
)
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


@router.get(
    "/{activity_id}/check-ins",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def get_club_activity_check_ins(
    club_id: int,
    activity_id: int,
    service: ClubActivityCheckInServiceDep,
    _: ClubRoleCheckerRequiresPresidentVice,
) -> Page[ClubActivityCheckInInfo]:
    """List an activity's check-in roster (president/vice-president only)."""
    return Page[ClubActivityCheckInInfo].model_validate(
        await service.get_check_ins(club_id, activity_id),
    )


@router.post(
    "/{activity_id}/check-ins",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def check_in_club_activity_manual(
    club_id: int,
    activity_id: int,
    obj_in: ClubActivityManualCheckInRequest,
    service: ClubActivityCheckInServiceDep,
    recorder: Annotated[User, Depends(get_current_user)],
    _: ClubRoleCheckerRequiresPresidentVice,
) -> list[ClubActivityCheckInInfo]:
    """(President/vice-president) record the roster of members who attended,
    after the fact. Resubmitting the same user ids is a no-op for them.
    """
    return [
        ClubActivityCheckInInfo.model_validate(check_in)
        for check_in in await service.check_in_manual(
            club_id,
            activity_id,
            obj_in.user_ids,
            recorder,
        )
    ]


@router.post(
    "/{activity_id}/check-in-qrcode",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def generate_club_activity_check_in_qrcode(
    club_id: int,
    activity_id: int,
    service: ClubActivityCheckInServiceDep,
    _: ClubRoleCheckerRequiresPresidentVice,
) -> ClubActivityCheckInQrTokenInfo:
    """(President/vice-president) mint a check-in token to render as a QR
    code. Only works while the activity is in progress, and the token
    expires with it.
    """
    token, expires_at = await service.generate_qr_token(club_id, activity_id)
    return ClubActivityCheckInQrTokenInfo(token=token, expires_at=expires_at)


@router.post(
    "/{activity_id}/check-in-qrcode/scan",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE,
)
async def scan_club_activity_check_in_qrcode(
    club_id: int,
    activity_id: int,
    obj_in: ClubActivityQrCheckInRequest,
    service: ClubActivityCheckInServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubActivityCheckInInfo:
    """Self check-in by scanning the activity's QR code. Any logged-in club
    member may call this — no president/vice-president role required.
    """
    return ClubActivityCheckInInfo.model_validate(
        await service.check_in_via_qr(club_id, activity_id, obj_in.token, user),
    )
