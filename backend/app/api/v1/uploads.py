from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import HttpUrl

from app.api.dependencies import ObjectStorageServiceDep, get_current_user
from app.schemas.upload import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    InitiateUploadRequest,
    InitiateUploadResponse,
    oss_public_base_url,
)
from app.services.upload_policy import (
    UPLOAD_POLICIES,
    validate_confirmed_upload,
    validate_file,
)

router = APIRouter(tags=["Uploads"])


@router.post(
    "/initiate",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
async def initiate_upload(
    req: InitiateUploadRequest,
    oss_service: ObjectStorageServiceDep,
) -> InitiateUploadResponse:
    policy = UPLOAD_POLICIES[req.scene]
    validate_file(policy, req)
    object_key = f"{policy.oss_dir}/{uuid4().hex}/{req.sanitized_filename}"
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
    dependencies=[Depends(get_current_user)],
)
async def confirm_upload(
    req: ConfirmUploadRequest,
    oss_service: ObjectStorageServiceDep,
) -> ConfirmUploadResponse:
    policy = UPLOAD_POLICIES[req.scene]
    actual_size = await oss_service.stat_object(req.object_key)
    validate_confirmed_upload(policy, req.object_key, actual_size)
    url = f"{oss_public_base_url()}/{req.object_key}"
    return ConfirmUploadResponse(url=HttpUrl(url))
