from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.settings import settings

if TYPE_CHECKING:
    from app.models.club import Club


class TagStatusEnum(StrEnum):
    normal = "normal"
    archived = "archived"


class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(
        String(settings.tag_max_name_length),
        unique=True,
        index=True,
    )
    status: Mapped[TagStatusEnum] = mapped_column(default=TagStatusEnum.normal)
    clubs: Mapped[list[Club]] = relationship(back_populates="tags")
