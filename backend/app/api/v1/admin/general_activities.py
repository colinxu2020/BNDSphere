from fastapi import APIRouter, HTTPException

from app.api.dependencies import GeneralActivityServiceDep
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
