from datetime import date

from sqlalchemy import (
    Boolean,
    Connection,
    Date,
    ForeignKey,
    Index,
    String,
    event,
    inspect,
    select,
)
from sqlalchemy.orm import Mapped, Mapper, declared_attr, mapped_column, relationship

from app.core import constants
from app.core.database import Base


class AcademicTerm(Base):
    __tablename__ = "academic_term"

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

    __table_args__ = (
        Index(
            "ix_only_one_current",
            "is_current",
            unique=True,
            postgresql_where=is_current.is_(True),
        ),
    )


@event.listens_for(AcademicTerm, "before_insert")
def handle_term_insert(
    mapper: Mapper[AcademicTerm],  # noqa: ARG001
    connection: Connection,  # noqa: ARG001
    target: AcademicTerm,
) -> None:
    if not target.term_name and target.start_date:
        target.term_name = AcademicTerm.calc_term_name(target.start_date)


@event.listens_for(AcademicTerm, "before_update")
def handle_term_update(
    mapper: Mapper[AcademicTerm],  # noqa: ARG001
    connection: Connection,  # noqa: ARG001
    target: AcademicTerm,
) -> None:
    state = inspect(target)
    start_date_changed = state.attrs.start_date.history.has_changes()
    term_name_changed = state.attrs.term_name.history.has_changes()
    if start_date_changed and not term_name_changed:
        target.term_name = AcademicTerm.calc_term_name(target.start_date)


class AcademicTermMixin:
    @declared_attr
    @classmethod
    def academic_term_id(cls) -> Mapped[int]:
        return mapped_column(
            ForeignKey("academic_term.id"),
            default=select(AcademicTerm.id)
            .where(AcademicTerm.is_current.is_(True))
            .scalar_subquery(),
        )

    @declared_attr
    @classmethod
    def academic_term(cls) -> Mapped[AcademicTerm]:
        return relationship(AcademicTerm, lazy="selectin")
