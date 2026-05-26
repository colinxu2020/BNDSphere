from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field

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


class InitiateUploadRequest(BaseModel):
    scene: UploadScene
    filename: str = Field(..., min_length=1)
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
    file_id: str
    object_key: str
    upload_url: str
    expires_seconds: int
