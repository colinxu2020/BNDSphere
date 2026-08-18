from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from fastapi import HTTPException, status

from app.schemas.upload import (
    SCENE_OSS_DIRS,
    InitiateUploadRequest,
    UploadScene,
    is_valid_object_key,
)
from app.services.errors import (
    UploadObjectNotFoundError,
    UploadObjectTooLargeError,
    UploadSceneMismatchError,
)

IMAGE_MAX_SIZE: Final = 5 * 1024 * 1024
IMAGE_ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/webp"},
)
IMAGE_ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {"jpg", "jpeg", "png", "webp"},
)
APPLICATION_FILE_MAX_SIZE: Final = 50 * 1024 * 1024
APPLICATION_FILE_ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "application/msword",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
)
APPLICATION_FILE_ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {"doc", "docx", "pdf"},
)


@dataclass(frozen=True, slots=True)
class UploadPolicy:
    scene: UploadScene
    max_size: int
    allowed_content_types: frozenset[str]
    allowed_extensions: frozenset[str]
    oss_dir: str
    expires_seconds: int = 600


def image_upload_policy(scene: UploadScene, oss_dir: str) -> UploadPolicy:
    return UploadPolicy(
        scene=scene,
        max_size=IMAGE_MAX_SIZE,
        allowed_content_types=IMAGE_ALLOWED_CONTENT_TYPES,
        allowed_extensions=IMAGE_ALLOWED_EXTENSIONS,
        oss_dir=oss_dir,
    )


UPLOAD_POLICIES: Mapping[UploadScene, UploadPolicy] = MappingProxyType(
    {
        UploadScene.AVATAR: image_upload_policy(
            scene=UploadScene.AVATAR,
            oss_dir=SCENE_OSS_DIRS[UploadScene.AVATAR],
        ),
        UploadScene.CLUB_LOGO: image_upload_policy(
            scene=UploadScene.CLUB_LOGO,
            oss_dir=SCENE_OSS_DIRS[UploadScene.CLUB_LOGO],
        ),
        UploadScene.ACTIVITY_POSTER: image_upload_policy(
            scene=UploadScene.ACTIVITY_POSTER,
            oss_dir="activity_poster",
        ),
        UploadScene.APPLICATION_FILE: UploadPolicy(
            scene=UploadScene.APPLICATION_FILE,
            max_size=APPLICATION_FILE_MAX_SIZE,
            allowed_content_types=APPLICATION_FILE_ALLOWED_CONTENT_TYPES,
            allowed_extensions=APPLICATION_FILE_ALLOWED_EXTENSIONS,
            oss_dir=SCENE_OSS_DIRS[UploadScene.APPLICATION_FILE],
        ),
    },
)


def validate_file(policy: UploadPolicy, req: InitiateUploadRequest) -> None:
    if req.size > policy.max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    if req.content_type not in policy.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content type",
        )

    if req.extension not in policy.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension",
        )


def validate_confirmed_upload(
    policy: UploadPolicy,
    object_key: str,
    actual_size: int | None,
) -> None:
    """校验一次已完成的上传: 对象确实存在, 且实际大小未超出策略上限.

    ``actual_size`` 来自 OSS 的 HEAD 请求, 不是客户端上报的 size, 因此能堵住
    ``initiate`` 阶段 size 校验被绕过 (预签名 URL 本身不限制实际上传大小) 的问题.
    """
    if not is_valid_object_key(object_key, policy.oss_dir):
        raise UploadSceneMismatchError(policy.scene.value)
    if actual_size is None:
        raise UploadObjectNotFoundError(object_key)
    if actual_size > policy.max_size:
        raise UploadObjectTooLargeError(object_key, policy.max_size)
