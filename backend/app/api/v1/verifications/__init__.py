from fastapi import APIRouter, Depends

from app.api.common_responses import (
    PERMISSION_DENIED_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    TOKEN_INVALID_RESPONSE,
)
from app.api.dependencies import ClubRoleChecker
from app.api.v1.verifications.club_memberships import router as club_memberships_router
from app.models.clubmember import ClubMembershipEnum

router = APIRouter(
    dependencies=[
        Depends(
            ClubRoleChecker(
                [ClubMembershipEnum.president, ClubMembershipEnum.vice_president],
            ),
        ),
    ],
    responses=(
        PERMISSION_DENIED_RESPONSE
        | TOKEN_INVALID_RESPONSE
        | RESOURCE_NOT_FOUND_RESPONSE
    ),
)
router.include_router(club_memberships_router, prefix="/membership-requests")
