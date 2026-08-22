from fastapi import APIRouter
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import JointActivityServiceDep
from app.schemas.joint_activities import JointActivityInfo

router = APIRouter(tags=["Joint Activities"])


@router.get("/")
async def list_joint_activities(
    service: JointActivityServiceDep,
    search: str | None = None,
) -> Page[JointActivityInfo]:
    """List pre-approved joint activities for public viewing."""
    return Page[JointActivityInfo].model_validate(
        await service.list_public(search),
    )


@router.get(
    "/{activity_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def get_joint_activity(
    activity_id: int,
    service: JointActivityServiceDep,
) -> JointActivityInfo:
    """Get a pre-approved joint activity for public viewing."""
    return JointActivityInfo.model_validate(await service.get_public(activity_id))
