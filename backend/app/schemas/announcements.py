from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.generic import IdMixin
from app.services.errors import BadRequestError


class AnnouncementBase(BaseModel):
    title: str = Field(..., max_length=120)
    body: str = Field(..., max_length=2000)
    link_url: str | None = Field(None, max_length=2048)
    starts_at: datetime | None = Field(None)
    ends_at: datetime | None = Field(None)
    is_active: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at < self.starts_at
        ):
            raise BadRequestError(
                "error.announcement.invalid_time_range",
                "ANNOUNCEMENT_INVALID_TIME_RANGE",
            )
        return self


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str | None = Field(None, max_length=120)
    body: str | None = Field(None, max_length=2000)
    link_url: str | None = Field(None, max_length=2048)
    starts_at: datetime | None = Field(None)
    ends_at: datetime | None = Field(None)
    is_active: bool | None = Field(None)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at < self.starts_at
        ):
            raise BadRequestError(
                "error.announcement.invalid_time_range",
                "ANNOUNCEMENT_INVALID_TIME_RANGE",
            )
        return self


class AnnouncementInfo(AnnouncementBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
