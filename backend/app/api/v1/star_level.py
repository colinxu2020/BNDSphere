from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page

from app.api.common_responses import (
    PERMISSION_DENIED_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    TOKEN_INVALID_RESPONSE,
)
from app.api.dependencies import (
    ClubMemberServiceDep,
    ClubServiceDep,
    StarLevelServiceDep,
    get_current_user,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import AuditStatusEnum, User
from app.schemas.star_level import (
    StarLevelApplicationInfo,
    StarLevelApplicationPublicInfo,
    StarLevelApplicationUpdate,
)
from app.services.errors import (
    StarLevelApplicationUpdateDeniedError,
    StarLevelNotFoundError,
)
from app.services.policies import AccessPolicy

router = APIRouter(tags=["Star Level"])


@router.get("/")
async def list_public_applications(
    service: StarLevelServiceDep,
) -> Page[StarLevelApplicationPublicInfo]:
    """List all star level applications, newest first."""
    return Page[StarLevelApplicationPublicInfo].model_validate(
        await service.list_public(),
    )


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
    responses=TOKEN_INVALID_RESPONSE
    | PERMISSION_DENIED_RESPONSE
    | RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_application(
    star_level_id: int,
    update: StarLevelApplicationUpdate,
    service: StarLevelServiceDep,
    club_service: ClubServiceDep,
    club_member_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> StarLevelApplicationInfo:
    """Update a star level application.
    Only the club president can perform this operation.
    """
    star_level = await service.get(star_level_id)
    if star_level is None:
        raise StarLevelNotFoundError(star_level_id) from None
    club = await club_service.ensure_club_normal(star_level.club_id)
    membership = await club_member_service.get_by_club_user(club, user)
    AccessPolicy.ensure_club_role_allowed(
        user,
        club,
        membership,
        [ClubMembershipEnum.president],
    )
    if star_level.audit_status == AuditStatusEnum.approved:
        raise StarLevelApplicationUpdateDeniedError(star_level_id) from None
    return StarLevelApplicationInfo.model_validate(
        await service.update(star_level, update),
    )
