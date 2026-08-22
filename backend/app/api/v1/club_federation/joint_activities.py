from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import JointActivityServiceDep, get_current_user
from app.models.user import User
from app.schemas.joint_activities import (
    JointActivityFinalReview,
    JointActivityInfo,
    JointActivityPreliminaryReview,
)

router = APIRouter(tags=["Federation: Joint Activities"])


@router.get("/")
async def list_joint_activities_for_federation(
    service: JointActivityServiceDep,
    search: str | None = None,
) -> Page[JointActivityInfo]:
    return Page[JointActivityInfo].model_validate(
        await service.list_for_federation(search),
    )


@router.patch(
    "/{activity_id}/preliminary-review",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def review_joint_activity_preliminarily(
    activity_id: int,
    obj_in: JointActivityPreliminaryReview,
    service: JointActivityServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> JointActivityInfo:
    return JointActivityInfo.model_validate(
        await service.preliminary_review(activity_id, obj_in, user),
    )


@router.patch(
    "/{activity_id}/final-review",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def review_joint_activity_finally(
    activity_id: int,
    obj_in: JointActivityFinalReview,
    service: JointActivityServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> JointActivityInfo:
    return JointActivityInfo.model_validate(
        await service.final_review(activity_id, obj_in, user),
    )
