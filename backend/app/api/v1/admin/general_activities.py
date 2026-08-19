from fastapi import APIRouter, status
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import GeneralActivityServiceDep
from app.models.general_activity import GeneralActivityLevelEnum
from app.schemas.general_activities import (
    GeneralActivityCreate,
    GeneralActivityInfo,
    GeneralActivityUpdate,
)
from app.services.errors import GeneralActivityNotFoundError

router = APIRouter(tags=["Admin: General Activities"])


@router.get("/")
async def list_general_activities(
    service: GeneralActivityServiceDep,
    search: str | None = None,
    level: GeneralActivityLevelEnum | None = None,
) -> Page[GeneralActivityInfo]:
    """List general activities for admin."""
    return Page[GeneralActivityInfo].model_validate(
        await service.get_multi(search, level),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_general_activity(
    obj_in: GeneralActivityCreate,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Create a general activity."""
    return GeneralActivityInfo.model_validate(await service.create(obj_in))


@router.patch(
    "/{activity_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_general_activity(
    activity_id: int,
    obj_in: GeneralActivityUpdate,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Update a general activity."""
    activity = await service.get(activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(activity_id) from None
    return GeneralActivityInfo.model_validate(await service.update(activity, obj_in))


@router.delete(
    "/{activity_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def delete_general_activity(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Delete a general activity."""
    activity = await service.get(activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(activity_id) from None
    await service.delete(activity)
    return GeneralActivityInfo.model_validate(activity)
