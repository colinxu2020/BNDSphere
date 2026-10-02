import hashlib
import hmac
import logging
import secrets
from typing import Annotated, Final

from fastapi import APIRouter, Depends, status
from pydantic import HttpUrl

from app.api.dependencies import ObjectStorageServiceDep, get_current_user
from app.core.settings import web_settings
from app.models.user import RoleEnum, User
from app.schemas.upload import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    InitiateUploadRequest,
    InitiateUploadResponse,
    UploadScene,
    oss_public_base_url,
)
from app.services.errors import UploadObjectTooLargeError
from app.services.policies import AccessPolicy
from app.services.upload_policy import (
    UPLOAD_POLICIES,
    validate_confirmed_upload,
    validate_file,
)

router = APIRouter(tags=["Uploads"])
logger = logging.getLogger(__name__)
RESOURCE_UPLOAD_ROLES: Final[list[RoleEnum]] = [
    RoleEnum.federation_staff,
    RoleEnum.admin,
    RoleEnum.dev,
]
_OWNER_TAG_CONTEXT: Final = b"bndsphere:upload-owner:v1"
_NONCE_HEX_LENGTH: Final = 16


def owner_tag(user_id: int, nonce: str) -> str:
    message = _OWNER_TAG_CONTEXT + f":{user_id}:{nonce}".encode()
    digest = hmac.digest(web_settings().secret_key.encode(), message, hashlib.sha256)
    return digest.hex()[:_NONCE_HEX_LENGTH]


def new_file_id(user: User) -> str:
    # Same 32-hex shape as the uuid4().hex it replaces: a random nonce plus an
    # HMAC tag binding it to the initiating user, so confirm can prove
    # ownership without a stored upload record.
    nonce = secrets.token_hex(_NONCE_HEX_LENGTH // 2)
    return nonce + owner_tag(user.id, nonce)


def initiated_by(object_key: str, user: User) -> bool:
    """Whether ``user`` initiated the upload of ``{oss_dir}/{file_id}/{name}``."""
    match object_key.split("/"):
        case [_, file_id, _]:
            nonce, tag = file_id[:_NONCE_HEX_LENGTH], file_id[_NONCE_HEX_LENGTH:]
            return hmac.compare_digest(tag, owner_tag(user.id, nonce))
        case _:
            return False


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
    file_id = new_file_id(user)
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
    try:
        validate_confirmed_upload(policy, req.object_key, actual_size)
    except UploadObjectTooLargeError:
        # Same-scene keys are guessable (avatar URLs are public), so only the
        # initiator's own oversized upload is cleaned up; anyone else just
        # gets the error.
        if initiated_by(req.object_key, user):
            try:
                await oss_service.delete_object(req.object_key)
            except Exception:
                logger.exception(
                    "Failed to delete oversized uploaded object %s",
                    req.object_key,
                )
        raise
    url = f"{oss_public_base_url()}/{req.object_key}"
    return ConfirmUploadResponse(url=HttpUrl(url))
