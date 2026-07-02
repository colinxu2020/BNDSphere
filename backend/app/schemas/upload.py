from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Final
from urllib.parse import unquote, urlsplit

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


def oss_public_base_url() -> str:
    """规范化后的公共访问域名 (去掉末尾的 '/', 避免拼接出双斜杠)."""
    return oss_settings().oss_public_base_url.rstrip("/")


def is_valid_object_key(object_key: str, oss_dir: str) -> bool:
    """确认 object_key 落在 ``oss_dir`` 目录下, 且不包含穿越/空路径段.

    仅比较原始字符串前缀无法防御 ``avatar/../application_files/x`` 这类请求 —
    浏览器/CDN 通常会在转发前按 RFC 3986 折叠 ``..`` 路径段, 从而让请求实际落到
    另一个 scene 的目录下。逐段校验 (拒绝空段、``.``、``..``) 才能堵住这个绕过。
    """
    segments = object_key.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        return False
    return segments[0] == oss_dir


def ensure_uploaded_object_url(
    scene: UploadScene,
    url: HttpUrl | None,
) -> HttpUrl | None:
    """限制字段只能引用通过 /uploads/initiate + /uploads/confirm 上传的对象.

    否则用户可以绕过全部大小/类型校验, 直接把 avatar_uri/logo_uri 设为任意外部 URL.
    """
    if url is None:
        return url

    base = urlsplit(oss_public_base_url())
    target = urlsplit(str(url))
    if (target.scheme, target.netloc) != (base.scheme, base.netloc):
        raise ValueError(f"{scene.value} URL must be hosted on the OSS public domain")
    if target.query or target.fragment:
        raise ValueError(f"{scene.value} URL must not contain a query or fragment")

    base_path = base.path
    target_path = unquote(target.path)
    if not target_path.startswith(f"{base_path}/"):
        raise ValueError(f"{scene.value} URL must reference an uploaded object")

    object_key = target_path[len(base_path) + 1 :]
    if not is_valid_object_key(object_key, SCENE_OSS_DIRS[scene]):
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
