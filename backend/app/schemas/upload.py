from enum import StrEnum

from pydantic import BaseModel, Field


def _filename_base(filename: str) -> str:
    return filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()


class UploadScene(StrEnum):
    AVATAR = "avatar"
    CLUB_LOGO = "club_logo"
    ACTIVITY_POSTER = "activity_poster"
    APPLICATION_FILE = "application_file"


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

    def storage_filename(self, file_id: str) -> str:
        if not self.extension:
            return file_id
        return f"{file_id}.{self.extension}"


class InitiateUploadResponse(BaseModel):
    file_id: str
    object_key: str
    upload_url: str
    expires_seconds: int
