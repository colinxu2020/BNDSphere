from fastapi import APIRouter, HTTPException

from app.api.dependencies import GeneralActivityServiceDep
from app.models.general_activity import GeneralActivityLevelEnum
from app.schemas.general_activities import (
    GeneralActivityInfo,
)

router = APIRouter(tags=["general activities"])


@router.get("/{activity_id}")
async def get(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    activity = await service.get(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return GeneralActivityInfo.model_validate(activity)


@router.get("/")
async def list_activities(
    service: GeneralActivityServiceDep,
    search: str | None = None,
    level: GeneralActivityLevelEnum | None = None,
) -> list[GeneralActivityInfo]:
    return [
        GeneralActivityInfo.model_validate(c)
        for c in await service.get_multi(search, level)
    ]
