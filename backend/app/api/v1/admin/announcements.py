from fastapi import APIRouter, status
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import AnnouncementServiceDep
from app.schemas.announcements import (
    AnnouncementCreate,
    AnnouncementInfo,
    AnnouncementUpdate,
)
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["Admin: Announcements"])


@router.get("/")
async def list_announcements(
    *,
    service: AnnouncementServiceDep,
    search: str | None = None,
    active_only: bool = False,
) -> Page[AnnouncementInfo]:
    """List announcements for admin."""
    return Page[AnnouncementInfo].model_validate(
        await service.get_multi(search, active_only=active_only),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_announcement(
    obj_in: AnnouncementCreate,
    service: AnnouncementServiceDep,
) -> AnnouncementInfo:
    """Create an announcement."""
    return AnnouncementInfo.model_validate(await service.create(obj_in))


@router.patch(
    "/{announcement_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_announcement(
    announcement_id: int,
    obj_in: AnnouncementUpdate,
    service: AnnouncementServiceDep,
) -> AnnouncementInfo:
    """Update an announcement."""
    announcement = await service.get(announcement_id)
    if announcement is None:
        raise ResourceNotFoundError(
            "error.announcement.not_found",
            "ANNOUNCEMENT_NOT_FOUND",
            {"announcement_id": announcement_id},
        ) from None
    return AnnouncementInfo.model_validate(await service.update(announcement, obj_in))


@router.delete(
    "/{announcement_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def delete_announcement(
    announcement_id: int,
    service: AnnouncementServiceDep,
) -> AnnouncementInfo:
    """Delete an announcement."""
    announcement = await service.get(announcement_id)
    if announcement is None:
        raise ResourceNotFoundError(
            "error.announcement.not_found",
            "ANNOUNCEMENT_NOT_FOUND",
            {"announcement_id": announcement_id},
        ) from None
    await service.delete(announcement)
    return AnnouncementInfo.model_validate(announcement)
