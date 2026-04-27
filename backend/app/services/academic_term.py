from typing import cast, override

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select, update

from app.models.academic_term import AcademicTerm
from app.schemas.academic_terms import AcademicTermCreate, AcademicTermUpdate
from app.services.base import ServiceBase


class AcademicTermService(
    ServiceBase[AcademicTerm, AcademicTermCreate, AcademicTermUpdate],
):
    model = AcademicTerm

    async def _clear_current_term(self) -> None:
        await self.db.execute(
            update(AcademicTerm)
            .where(AcademicTerm.is_current)
            .values(is_current=False),
        )

    async def get_multi(self) -> Page[AcademicTerm]:
        stmt = select(AcademicTerm).order_by(AcademicTerm.start_date.desc())
        return cast("Page[AcademicTerm]", await apaginate(self.db, stmt))

    async def set_current(self, term: AcademicTerm) -> AcademicTerm:
        await self._clear_current_term()
        term.is_current = True
        self.db.add(term)
        await self.db.flush()
        await self.db.refresh(term)
        return term

    @override
    async def create(
        self,
        obj_in: AcademicTermCreate,
        **kwargs: object,
    ) -> AcademicTerm:
        if obj_in.is_current:
            await self._clear_current_term()
        return await super().create(obj_in, **kwargs)
