from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Final

from pydantic import AfterValidator, BaseModel, Field, HttpUrl

from app.core.settings import oss_settings

SAFE_FILENAME_FALLBACK: Final[str] = "file"
SAFE_FILENAME_ALLOWED_CHARS: Final[frozenset[str]] = frozenset({".", "-", "_"})


def _filename_base(filename: str) -> str:
    return filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()


def _sanitize_filename_part(value: str) -> str:
    sanitized = "".join(
        char if char.isalnum() or char in SAFE_FILENAME_ALLOWED_CHARS else "_"
        for char in value
    )
    sanitized = "_".join(part for part in sanitized.split("_") if part)
    return sanitized.strip("._-") or SAFE_FILENAME_FALLBACK


class UploadScene(StrEnum):
    AVATAR = "avatar"
    CLUB_LOGO = "club_logo"
    APPLICATION_FILE = "application_file"


# Single source of truth for scene -> object-key prefix, shared by the upload
# policies (services/upload_policy.py) and the URL validators below, so a
# persisted avatar/logo URL always points into the directory it was actually
# uploaded to.
SCENE_OSS_DIRS: Final[MappingProxyType[UploadScene, str]] = MappingProxyType(
    {
        UploadScene.AVATAR: "avatar",
        UploadScene.CLUB_LOGO: "club_logo",
        UploadScene.APPLICATION_FILE: "application_files",
    },
)


def ensure_uploaded_object_url(
    scene: UploadScene,
    url: HttpUrl | None,
) -> HttpUrl | None:
    """限制字段只能引用通过 /uploads/initiate + /uploads/confirm 上传的对象.

    否则用户可以绕过全部大小/类型校验, 直接把 avatar_uri/logo_uri 设为任意外部 URL.
    """
    if url is None:
        return url
    prefix = f"{oss_settings().oss_public_base_url}/{SCENE_OSS_DIRS[scene]}/"
    if not str(url).startswith(prefix):
        raise ValueError(f"{scene.value} URL must reference an uploaded object")
    return url


def _validate_avatar_uri(url: HttpUrl | None) -> HttpUrl | None:
    return ensure_uploaded_object_url(UploadScene.AVATAR, url)


def _validate_logo_uri(url: HttpUrl | None) -> HttpUrl | None:
    return ensure_uploaded_object_url(UploadScene.CLUB_LOGO, url)


AvatarUri = Annotated[HttpUrl | None, AfterValidator(_validate_avatar_uri)]
LogoUri = Annotated[HttpUrl | None, AfterValidator(_validate_logo_uri)]


class InitiateUploadRequest(BaseModel):
    scene: UploadScene
    filename: str = Field(..., min_length=1, max_length=256)
    content_type: str
    size: int = Field(..., gt=0)

    @property
    def extension(self) -> str:
        base = _filename_base(self.filename)
        if "." not in base:
            return ""
        return base.rsplit(".", maxsplit=1)[-1].lower()

    @property
    def sanitized_filename(self) -> str:
        base = _filename_base(self.filename)
        stem, separator, extension = base.rpartition(".")
        if not separator:
            return _sanitize_filename_part(base)

        safe_stem = _sanitize_filename_part(stem)
        safe_extension = _sanitize_filename_part(extension.lower())
        return f"{safe_stem}.{safe_extension}"


class InitiateUploadResponse(BaseModel):
    object_key: str
    upload_url: str
    expires_seconds: int


class ConfirmUploadRequest(BaseModel):
    scene: UploadScene
    object_key: str = Field(..., min_length=1, max_length=512)


class ConfirmUploadResponse(BaseModel):
    url: HttpUrl
