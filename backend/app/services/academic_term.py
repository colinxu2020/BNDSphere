from typing import override

from fastapi_pagination import Page

from app.models.academic_term import AcademicTerm
from app.repositories.academic_term import AcademicTermRepository
from app.schemas.academic_terms import AcademicTermCreate, AcademicTermUpdate
from app.services.base import ServiceBase


class AcademicTermService(
    ServiceBase[
        AcademicTerm,
        AcademicTermCreate,
        AcademicTermUpdate,
    ],
):
    repository: AcademicTermRepository

    async def get_multi(self) -> Page[AcademicTerm]:
        return await self.repository.get_multi()

    async def set_current(self, term: AcademicTerm) -> AcademicTerm:
        await self.repository.clear_current_term()
        return await self.repository.set_current(term)

    @override
    async def create(
        self,
        obj_in: AcademicTermCreate,
        **kwargs: object,
    ) -> AcademicTerm:
        if obj_in.is_current:
            await self.repository.clear_current_term()
        return await super().create(obj_in, **kwargs)
