from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.tag import Tag


class ClubTag(Base):
    __tablename__ = "club_tags"

    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))

    tag: Mapped[Tag] = relationship(back_populates="clubs")
    club: Mapped[Club] = relationship(back_populates="tags")
