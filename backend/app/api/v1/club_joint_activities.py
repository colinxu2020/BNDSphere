from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import (
    PERMISSION_DENIED_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    TOKEN_INVALID_RESPONSE,
)
from app.api.dependencies import (
    ClubRoleChecker,
    ClubServiceDep,
    JointActivityServiceDep,
    get_current_user,
)
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.joint_activities import (
    JointActivityArchiveUpdate,
    JointActivityCreate,
    JointActivityInfo,
    JointActivityUpdate,
)

router = APIRouter(tags=["Club Joint Activities"])

manager_only = Depends(
    ClubRoleChecker(
        [ClubMembershipEnum.vice_president, ClubMembershipEnum.president],
    ),
)


@router.get(
    "/",
    dependencies=[manager_only],
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def list_club_joint_activities(
    club_id: int,
    club_service: ClubServiceDep,
    service: JointActivityServiceDep,
) -> Page[JointActivityInfo]:
    await club_service.ensure_club_normal(club_id)
    return Page[JointActivityInfo].model_validate(
        await service.list_for_club(club_id),
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[manager_only],
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
)
async def create_joint_activity(
    club_id: int,
    obj_in: JointActivityCreate,
    club_service: ClubServiceDep,
    service: JointActivityServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> JointActivityInfo:
    await club_service.ensure_club_normal(club_id)
    return JointActivityInfo.model_validate(
        await service.create_for_club(
            obj_in,
            club_id=club_id,
            user_id=user.id,
        ),
    )


@router.patch(
    "/{activity_id}",
    dependencies=[manager_only],
    responses=TOKEN_INVALID_RESPONSE
    | PERMISSION_DENIED_RESPONSE
    | RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_joint_activity(
    club_id: int,
    activity_id: int,
    obj_in: JointActivityUpdate,
    club_service: ClubServiceDep,
    service: JointActivityServiceDep,
) -> JointActivityInfo:
    await club_service.ensure_club_normal(club_id)
    return JointActivityInfo.model_validate(
        await service.update_for_initiator(activity_id, club_id, obj_in),
    )


@router.post(
    "/{activity_id}/participations",
    status_code=status.HTTP_201_CREATED,
    dependencies=[manager_only],
    responses=TOKEN_INVALID_RESPONSE
    | PERMISSION_DENIED_RESPONSE
    | RESOURCE_NOT_FOUND_RESPONSE,
)
async def register_joint_activity_participation(
    club_id: int,
    activity_id: int,
    club_service: ClubServiceDep,
    service: JointActivityServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> JointActivityInfo:
    await club_service.ensure_club_normal(club_id)
    return JointActivityInfo.model_validate(
        await service.register_participation(
            activity_id,
            club_id=club_id,
            user_id=user.id,
        ),
    )


@router.patch(
    "/{activity_id}/archive",
    dependencies=[manager_only],
    responses=TOKEN_INVALID_RESPONSE
    | PERMISSION_DENIED_RESPONSE
    | RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_joint_activity_archive(
    club_id: int,
    activity_id: int,
    obj_in: JointActivityArchiveUpdate,
    club_service: ClubServiceDep,
    service: JointActivityServiceDep,
) -> JointActivityInfo:
    await club_service.ensure_club_normal(club_id)
    return JointActivityInfo.model_validate(
        await service.update_archive(activity_id, club_id, obj_in),
    )


@router.post(
    "/{activity_id}/final-submission",
    dependencies=[manager_only],
    responses=TOKEN_INVALID_RESPONSE
    | PERMISSION_DENIED_RESPONSE
    | RESOURCE_NOT_FOUND_RESPONSE,
)
async def submit_joint_activity_final_review(
    club_id: int,
    activity_id: int,
    club_service: ClubServiceDep,
    service: JointActivityServiceDep,
) -> JointActivityInfo:
    await club_service.ensure_club_normal(club_id)
    return JointActivityInfo.model_validate(
        await service.submit_final_review(activity_id, club_id),
    )
