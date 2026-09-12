from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.generic import IdMixin

ASCII_CONTROL_END = 32
ASCII_DELETE = 127


class ResourceFileCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=256)
    object_key: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=1, max_length=255)

    @field_validator("filename")
    @classmethod
    def normalize_filename(cls, value: str) -> str:
        filename = value.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
        if filename in {"", ".", ".."} or any(
            ord(character) < ASCII_CONTROL_END or ord(character) == ASCII_DELETE
            for character in filename
        ):
            raise ValueError("Invalid filename")
        return filename


class ResourceFileInfo(IdMixin):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    content_type: str
    file_size: int
    created_at: datetime


class ResourceFileUpdate(BaseModel):
    """Resource files are immutable; this type satisfies the generic repository."""
