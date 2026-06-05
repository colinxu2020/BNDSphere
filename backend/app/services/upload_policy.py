from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from fastapi import HTTPException, status

from app.schemas.upload import InitiateUploadRequest, UploadScene

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
            oss_dir="avatar",
        ),
        UploadScene.CLUB_LOGO: image_upload_policy(
            scene=UploadScene.CLUB_LOGO,
            oss_dir="club_logo",
        ),
        UploadScene.APPLICATION_FILE: UploadPolicy(
            scene=UploadScene.APPLICATION_FILE,
            max_size=APPLICATION_FILE_MAX_SIZE,
            allowed_content_types=APPLICATION_FILE_ALLOWED_CONTENT_TYPES,
            allowed_extensions=APPLICATION_FILE_ALLOWED_EXTENSIONS,
            oss_dir="application_files",
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
