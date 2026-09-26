import logging
from typing import Annotated, Final

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from fastapi_pagination import Page

from app.api.common_responses import (
    PERMISSION_DENIED_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    TOKEN_INVALID_RESPONSE,
)
from app.api.dependencies import (
    ObjectStorageServiceDep,
    ResourceFileServiceDep,
    RoleChecker,
)
from app.models.user import RoleEnum, User
from app.schemas.resource_files import (
    PendingDeletionRetryResult,
    ResourceFileCreate,
    ResourceFileInfo,
)
from app.schemas.upload import UploadScene
from app.services.errors import (
    DuplicateResourceError,
    ResourceNotFoundError,
    UploadObjectTooLargeError,
)
from app.services.upload_policy import UPLOAD_POLICIES, validate_confirmed_upload

router = APIRouter(tags=["Resource Center"])
logger = logging.getLogger(__name__)

RESOURCE_MANAGER_ROLES: Final[list[RoleEnum]] = [
    RoleEnum.federation_staff,
    RoleEnum.admin,
    RoleEnum.dev,
]
ResourceManager = Annotated[User, Depends(RoleChecker(RESOURCE_MANAGER_ROLES))]


@router.get("/")
async def list_resource_files(
    *,
    service: ResourceFileServiceDep,
    search: str | None = None,
) -> Page[ResourceFileInfo]:
    """List files in the public resource center."""
    return Page[ResourceFileInfo].model_validate(await service.get_multi(search))


@router.post(
    "/retry-pending-deletions",
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
async def retry_pending_resource_deletions(
    service: ResourceFileServiceDep,
    oss_service: ObjectStorageServiceDep,
    _manager: ResourceManager,
) -> PendingDeletionRetryResult:
    """Retry object and database cleanup for all pending resource deletions."""
    pending_deletions = [
        (resource_file.id, resource_file.object_key)
        for resource_file in await service.get_pending_deletions()
    ]
    deleted = 0
    failed = 0
    for resource_id, object_key in pending_deletions:
        try:
            await oss_service.delete_object(object_key)
            await service.finish_deletion(resource_id)
        except Exception:
            failed += 1
            logger.exception(
                "Failed to retry pending resource deletion for resource %s",
                resource_id,
            )
        else:
            deleted += 1

    return PendingDeletionRetryResult(
        attempted=len(pending_deletions),
        deleted=deleted,
        failed=failed,
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
async def create_resource_file(
    obj_in: ResourceFileCreate,
    service: ResourceFileServiceDep,
    oss_service: ObjectStorageServiceDep,
    manager: ResourceManager,
) -> ResourceFileInfo:
    """Register an uploaded file in the resource center."""
    policy = UPLOAD_POLICIES[UploadScene.RESOURCE_FILE]
    actual_size = await oss_service.stat_object(obj_in.object_key)
    try:
        validate_confirmed_upload(policy, obj_in.object_key, actual_size)
    except UploadObjectTooLargeError:
        try:
            await oss_service.delete_object(obj_in.object_key)
        except Exception:
            logger.exception(
                "Failed to delete oversized uploaded object %s",
                obj_in.object_key,
            )
        raise
    if await service.get_by_object_key(obj_in.object_key) is not None:
        raise DuplicateResourceError(
            "error.resource_file.already_registered",
            "RESOURCE_FILE_ALREADY_REGISTERED",
            {"object_key": obj_in.object_key},
        )

    try:
        resource_file = await service.create(
            obj_in,
            file_size=actual_size,
            uploader_id=manager.id,
        )
    except DuplicateResourceError:
        # The object_key is owned by another record (live or pending deletion);
        # its object is that record's responsibility, do not touch it.
        raise
    except Exception:
        # Registration failed after the object was uploaded. Pending-deletion
        # cleanup only scans rows with deletion_requested_at set, so this
        # orphan would never be reclaimed; delete it as compensation.
        try:
            await oss_service.delete_object(obj_in.object_key)
        except Exception:
            logger.exception(
                "Failed to delete orphaned object %s after registration failure",
                obj_in.object_key,
            )
        raise
    return ResourceFileInfo.model_validate(resource_file)


@router.get(
    "/{resource_id}/download",
    response_class=RedirectResponse,
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def download_resource_file(
    resource_id: int,
    service: ResourceFileServiceDep,
    oss_service: ObjectStorageServiceDep,
) -> RedirectResponse:
    """Redirect anyone to a short-lived download URL."""
    resource_file = await service.get(resource_id)
    if resource_file is None:
        raise ResourceNotFoundError(
            "error.resource_file.not_found",
            "RESOURCE_FILE_NOT_FOUND",
            {"resource_id": resource_id},
        ) from None

    download_url = await oss_service.generate_get_presigned_url(
        resource_file.object_key,
        resource_file.filename,
    )
    return RedirectResponse(download_url)


@router.delete(
    "/{resource_id}",
    responses=(
        RESOURCE_NOT_FOUND_RESPONSE
        | PERMISSION_DENIED_RESPONSE
        | TOKEN_INVALID_RESPONSE
    ),
)
async def delete_resource_file(
    resource_id: int,
    service: ResourceFileServiceDep,
    oss_service: ObjectStorageServiceDep,
    _manager: ResourceManager,
) -> ResourceFileInfo:
    """Delete a resource-center file and its stored object."""
    resource_file = await service.prepare_deletion(resource_id)
    if resource_file is None:
        raise ResourceNotFoundError(
            "error.resource_file.not_found",
            "RESOURCE_FILE_NOT_FOUND",
            {"resource_id": resource_id},
        ) from None

    response = ResourceFileInfo.model_validate(resource_file)
    await oss_service.delete_object(resource_file.object_key)
    await service.finish_deletion(resource_file.id)
    return response
