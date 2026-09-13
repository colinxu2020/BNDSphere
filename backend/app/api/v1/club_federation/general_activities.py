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

router = APIRouter(tags=["Federation: General Activities"])


@router.get("/")
async def list_activities(
    *,
    service: GeneralActivityServiceDep,
    search: str | None = None,
    level: GeneralActivityLevelEnum | None = None,
) -> Page[GeneralActivityInfo]:
    """List general activities for federation review.

    Unlike the public list endpoint, club_records includes pending and rejected
    records so federation staff can review them.
    """
    return Page[GeneralActivityInfo].model_validate(
        await service.get_multi(search, level),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(
    obj: GeneralActivityCreate,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Create a new general activity."""
    return GeneralActivityInfo.model_validate(await service.create(obj))


@router.patch(
    "/{activity_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def update(
    activity_id: int,
    update: GeneralActivityUpdate,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Update the general activity with the given ID."""
    activity = await service.get(activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(activity_id)
    return GeneralActivityInfo.model_validate(await service.update(activity, update))


@router.delete(
    "/{activity_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def delete(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Delete the general activity with the given ID."""
    activity = await service.get(activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(activity_id)
    await service.delete(activity)
    return GeneralActivityInfo.model_validate(activity)
