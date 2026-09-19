from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import (
    ClubClaimRequestServiceDep,
    RoleChecker,
    get_current_user,
)
from app.models.user import RoleEnum, User
from app.schemas.verifications.club_claim import (
    ClubClaimRequestInfo,
    ClubClaimRequestReviewInfo,
)
from app.schemas.verifications.verification_common import RequestVerifyPublic

# Approving a claim appoints a club president, which docs/business_process.md
# documents as an admin act, so this router is narrower than its parent
# (which also admits federation staff).
router = APIRouter(
    tags=["Federation: Club Claims"],
    dependencies=[Depends(RoleChecker([RoleEnum.admin]))],
)


@router.get("/")
async def get_pending_claim_requests(
    service: ClubClaimRequestServiceDep,
) -> Page[ClubClaimRequestReviewInfo]:
    """List pending club claim requests."""
    return Page[ClubClaimRequestReviewInfo].model_validate(
        await service.get_pending_requests(),
    )


@router.patch(
    "/{request_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def verify_claim_request(
    request_id: int,
    obj_in: RequestVerifyPublic,
    service: ClubClaimRequestServiceDep,
    verifier: Annotated[User, Depends(get_current_user)],
) -> ClubClaimRequestInfo:
    """Approve or reject a club claim request."""
    return ClubClaimRequestInfo.model_validate(
        await service.verify_claim_request(request_id, obj_in, verifier),
    )
