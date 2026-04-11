from fastapi import APIRouter
from fastapi_pagination import Page

from app.api.dependencies import GeneralActivityServiceDep
from app.models.general_activity import GeneralActivityLevelEnum
from app.schemas.general_activities import (
    GeneralActivityInfo,
)
from app.services.errors import GeneralActivityNotFoundError

router = APIRouter(tags=["general activities"])


@router.get("/{activity_id}")
async def get(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    activity = await service.get(activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(activity_id) from None
    return GeneralActivityInfo.model_validate(activity)


@router.get("/")
async def list_activities(
    service: GeneralActivityServiceDep,
    search: str | None = None,
    level: GeneralActivityLevelEnum | None = None,
) -> Page[GeneralActivityInfo]:
    return Page[GeneralActivityInfo].model_validate(
        await service.get_multi(search, level),
    )
