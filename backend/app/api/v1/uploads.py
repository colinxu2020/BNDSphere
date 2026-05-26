from uuid import uuid4

from fastapi import APIRouter, status

from app.schemas.upload import InitiateUploadRequest, InitiateUploadResponse
from app.services.oss import ObjectStorageService
from app.services.upload_policy import UPLOAD_POLICIES, validate_file

router = APIRouter(tags=["Uploads"])


@router.post("/initiate", status_code=status.HTTP_201_CREATED)
async def initiate_upload(req: InitiateUploadRequest) -> InitiateUploadResponse:
    oss_service = ObjectStorageService()
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
        file_id="N/A",
    )
