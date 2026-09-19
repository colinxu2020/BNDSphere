from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import ClubClaimRequestServiceDep, get_current_user
from app.models.user import User
from app.schemas.verifications.club_claim import (
    ClubClaimRequestInfo,
    ClubClaimRequestReviewInfo,
)
from app.schemas.verifications.verification_common import RequestVerifyPublic

router = APIRouter(tags=["Federation: Club Claims"])


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
