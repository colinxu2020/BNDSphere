from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import ClubRoleChecker, StarLevelServiceDep
from app.models.clubmember import ClubMembershipEnum
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


@router.patch(
    "/{star_level_id}",
    dependencies=[Depends(ClubRoleChecker([ClubMembershipEnum.president]))],
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
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
