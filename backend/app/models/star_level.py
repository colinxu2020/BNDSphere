from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.academic_term import AcademicTermMixin
from app.models.club import ClubStarLevelEnum
from app.models.user import AuditMixin
from app.utils.custom_types import HttpUrlType

if TYPE_CHECKING:
    from app.models import Club


class StarLevelApplication(Base, AcademicTermMixin, AuditMixin):
    __tablename__ = "star_level_applications"

    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    club: Mapped[Club] = relationship()

    contest_attachment: Mapped[HttpUrl | None] = mapped_column(HttpUrlType)
    requested_contest_score: Mapped[int | None] = mapped_column()
    final_contest_score: Mapped[int | None] = mapped_column()
    uniqueness_statement: Mapped[str | None] = mapped_column(Text)
    uniqueness_approved: Mapped[bool | None] = mapped_column(Boolean)

    approved_score: Mapped[int | None] = mapped_column()
    approved_level: Mapped[ClubStarLevelEnum | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (UniqueConstraint("club_id", "academic_term_id"),)
