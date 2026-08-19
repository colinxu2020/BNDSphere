from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import StarLevelServiceDep, get_current_user
from app.models.user import User
from app.schemas.star_level import (
    StarLevelApplicationInfo,
    StarLevelApplicationReview,
    StarLevelApplicationReviewPreview,
)

router = APIRouter(tags=["Club Federation: Star Level"])


@router.post("/{star_level_id}/preview")
async def preview_star_level_application_review(
    star_level_id: int,
    review: StarLevelApplicationReview,
    service: StarLevelServiceDep,
) -> StarLevelApplicationReviewPreview:
    return await service.preview_review(star_level_id, review)


@router.patch("/{star_level_id}")
async def review_star_level_application(
    star_level_id: int,
    review: StarLevelApplicationReview,
    service: StarLevelServiceDep,
    auditor: Annotated[User, Depends(get_current_user)],
) -> StarLevelApplicationInfo:
    return StarLevelApplicationInfo.model_validate(
        await service.review(star_level_id, review, auditor),
    )
