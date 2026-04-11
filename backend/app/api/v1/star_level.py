from fastapi import APIRouter

from app.api.dependencies import StarLevelServiceDep
from app.models.user import AuditStatusEnum
from app.schemas.star_level import StarLevelApplicationInfo, StarLevelApplicationUpdate
from app.services.errors import (
    StarLevelApplicationUpdateDeniedError,
    StarLevelNotFoundError,
)

router = APIRouter(tags=["Star Level"])


@router.get("/{star_level_id}")
async def get_by_id(
    star_level_id: int,
    service: StarLevelServiceDep,
) -> StarLevelApplicationInfo:
    star_level = await service.get(star_level_id)
    if star_level is None:
        raise StarLevelNotFoundError(star_level_id) from None
    return StarLevelApplicationInfo.model_validate(star_level)


@router.patch("/{star_level_id}")
async def update_application(
    star_level_id: int,
    update: StarLevelApplicationUpdate,
    service: StarLevelServiceDep,
) -> StarLevelApplicationInfo:
    star_level = await service.get(star_level_id)
    if star_level is None:
        raise StarLevelNotFoundError(star_level_id) from None
    if star_level.audit_status == AuditStatusEnum.approved:
        raise StarLevelApplicationUpdateDeniedError(star_level_id) from None
    return StarLevelApplicationInfo.model_validate(
        await service.update(star_level, update),
    )
