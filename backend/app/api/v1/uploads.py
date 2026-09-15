from typing import Annotated, Final
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import HttpUrl

from app.api.dependencies import ObjectStorageServiceDep, get_current_user
from app.models.user import RoleEnum, User
from app.schemas.upload import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    InitiateUploadRequest,
    InitiateUploadResponse,
    UploadScene,
    oss_public_base_url,
)
from app.services.policies import AccessPolicy
from app.services.upload_policy import (
    UPLOAD_POLICIES,
    validate_confirmed_upload,
    validate_file,
)

router = APIRouter(tags=["Uploads"])
RESOURCE_UPLOAD_ROLES: Final[list[RoleEnum]] = [
    RoleEnum.federation_staff,
    RoleEnum.admin,
    RoleEnum.dev,
]


def ensure_scene_access(scene: UploadScene, user: User) -> None:
    if scene == UploadScene.RESOURCE_FILE:
        AccessPolicy.ensure_role_allowed(user, RESOURCE_UPLOAD_ROLES)


@router.post(
    "/initiate",
    status_code=status.HTTP_201_CREATED,
)
async def initiate_upload(
    req: InitiateUploadRequest,
    oss_service: ObjectStorageServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> InitiateUploadResponse:
    ensure_scene_access(req.scene, user)
    policy = UPLOAD_POLICIES[req.scene]
    validate_file(policy, req)
    file_id = uuid4().hex
    object_key = f"{policy.oss_dir}/{file_id}/{req.storage_filename(file_id)}"
    upload_url = await oss_service.generate_put_presigned_url(
        object_key,
        req.content_type,
        policy.expires_seconds,
    )
    return InitiateUploadResponse(
        object_key=object_key,
        upload_url=upload_url,
        expires_seconds=policy.expires_seconds,
    )


@router.post(
    "/confirm",
)
async def confirm_upload(
    req: ConfirmUploadRequest,
    oss_service: ObjectStorageServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ConfirmUploadResponse:
    ensure_scene_access(req.scene, user)
    policy = UPLOAD_POLICIES[req.scene]
    actual_size = await oss_service.stat_object(req.object_key)
    validate_confirmed_upload(policy, req.object_key, actual_size)
    url = f"{oss_public_base_url()}/{req.object_key}"
    return ConfirmUploadResponse(url=HttpUrl(url))
