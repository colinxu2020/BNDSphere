from datetime import datetime

from fastapi import APIRouter
from fastapi_pagination import Page

from app.api.dependencies import GeneralActivityServiceDep
from app.models.general_activity import GeneralActivityLevelEnum
from app.schemas.general_activities import (
    GeneralActivityInfo,
)
from app.services.errors import GeneralActivityNotFoundError

router = APIRouter(tags=["General Activities"])


@router.get("/{activity_id}")
async def get(
    activity_id: int,
    service: GeneralActivityServiceDep,
) -> GeneralActivityInfo:
    """Get the general activity with the given ID."""
    activity = await service.get(activity_id)
    if activity is None:
        raise GeneralActivityNotFoundError(activity_id) from None
    return GeneralActivityInfo.model_validate(activity)


@router.get("/")
async def list_activities(
    *,
    service: GeneralActivityServiceDep,
    search: str | None = None,
    level: GeneralActivityLevelEnum | None = None,
    starts_before: datetime | None = None,
    ends_after: datetime | None = None,
    has_poster: bool | None = None,
) -> Page[GeneralActivityInfo]:
    """List general activities.
    Optionally filtered by search keyword and/or activity level.
    """
    return Page[GeneralActivityInfo].model_validate(
        await service.get_multi(
            search,
            level,
            starts_before=starts_before,
            ends_after=ends_after,
            has_poster=has_poster,
        ),
    )
