from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.dependencies import (
    ClubMembershipRequestServiceDep,
    get_current_user,
)
from app.models.user import User
from app.schemas.verifications.club_membership import ClubMembershipRequestInfo
from app.schemas.verifications.verification_common import RequestVerifyPublic

router = APIRouter(tags=["Verification: Club Memberships"])


@router.get(
    "",
)
async def get_pending_membership_requests(
    club_id: int,
    service: ClubMembershipRequestServiceDep,
) -> Page[ClubMembershipRequestInfo]:
    """Get pending club membership requests for the club."""
    return Page[ClubMembershipRequestInfo].model_validate(
        await service.get_pending_requests(club_id),
    )


@router.patch(
    "/{request_id}",
)
async def verify_membership_request(
    club_id: int,
    request_id: int,
    obj_in: RequestVerifyPublic,
    service: ClubMembershipRequestServiceDep,
    verifier: Annotated[User, Depends(get_current_user)],
) -> ClubMembershipRequestInfo:
    """Verify (approve / reject) a club membership request."""
    return ClubMembershipRequestInfo.model_validate(
        await service.verify_membership_request(
            club_id,
            request_id,
            obj_in,
            verifier,
        ),
    )
