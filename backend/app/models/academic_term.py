from datetime import date

from sqlalchemy import Boolean, Connection, Date, String, event
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.core import constants
from app.core.database import Base


class AcademicTerm(Base):
    term_name: Mapped[str] = mapped_column(
        String(constants.ACADEMIC_TERM_MAX_LENGTH),
        unique=True,
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    @staticmethod
    def calc_term_name(start_date: date) -> str:
        if start_date.month == 9:  # noqa: PLR2004
            return f"{start_date.year} - {start_date.year + 1} - 1"
        return f"{start_date.year - 1} - {start_date.year} - 2"


@event.listens_for(AcademicTerm, "before_insert")
@event.listens_for(AcademicTerm, "before_update")
def handle_term_data(
    mapper: Mapper,  # noqa: ARG001
    connection: Connection,  # noqa: ARG001
    target: AcademicTerm,
) -> None:
    if not target.term_name and target.start_date:
        target.term_name = AcademicTerm.calc_term_name(target.start_date)
