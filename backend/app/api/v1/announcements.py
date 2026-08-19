from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi_pagination import Page

from app.api.dependencies import AnnouncementServiceDep
from app.schemas.announcements import AnnouncementInfo

router = APIRouter(tags=["Announcements"])


@router.get("/")
async def list_announcements(
    *,
    service: AnnouncementServiceDep,
    search: str | None = None,
    active_only: bool = True,
) -> Page[AnnouncementInfo]:
    """List announcements for the homepage."""
    at_time = datetime.now(tz=UTC) if active_only else None
    return Page[AnnouncementInfo].model_validate(
        await service.get_multi(search, active_only=active_only, at_time=at_time),
    )
