from collections.abc import Sequence

from sqlalchemy import select

from app.models.academic_term import AcademicTerm
from app.schemas.academic_terms import AcademicTermCreate, AcademicTermUpdate
from app.services.base import ServiceBase


class AcademicTermService(
    ServiceBase[AcademicTerm, AcademicTermCreate, AcademicTermUpdate],
):
    model = AcademicTerm

    async def get_muli(self) -> Sequence[AcademicTerm]:
        stmt = select(AcademicTerm).order_by(AcademicTerm.start_date.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()
