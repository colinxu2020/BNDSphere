from fastapi import APIRouter, HTTPException

from app.api.dependencies import GeneralActivityServiceDep
from app.models.general_activity import GeneralActivityLevelEnum
from app.schemas.general_activities import (
    GeneralActivityCreate,
    GeneralActivityInfo,
    GeneralActivityUpdate,
)

router = APIRouter(tags=["general activities"])


@router.post("/")
async def create(
    obj: GeneralActivityCreate,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    return GeneralActivityInfo.model_validate(await service.create(obj))


@router.get("/{activity_id}")
async def get(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    activity = await service.get(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return GeneralActivityInfo.model_validate(activity)


@router.patch("/{activity_id}")
async def update(
    activity_id: int,
    update: GeneralActivityUpdate,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    activity = await service.get(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return GeneralActivityInfo.model_validate(service.update(activity, update))


@router.delete("/{activity_id}")
async def delete(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    activity = await service.get(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    await service.delete(activity)
    return GeneralActivityInfo.model_validate(activity)


@router.get("/")
async def list_activities(
    service: GeneralActivityServiceDep,
    search: str | None = None,
    level: GeneralActivityLevelEnum | None = None,
) -> list[GeneralActivityInfo]:
    return [
        GeneralActivityInfo.model_validate(c)
        for c in await service.get_muli(search, level)
    ]
