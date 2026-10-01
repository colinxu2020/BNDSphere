from typing import override

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models.academic_term import AcademicTerm
from app.repositories.academic_term import AcademicTermRepository
from app.schemas.academic_terms import AcademicTermCreate, AcademicTermUpdate
from app.services.base import ServiceBase
from app.services.errors import BusinessError

_TERM_UNIQUE_CONSTRAINTS = {"uq_academic_terms_term_name", "ix_only_one_current"}


def _raise_known_term_conflict(exc: IntegrityError) -> None:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name in _TERM_UNIQUE_CONSTRAINTS:
        raise BusinessError(
            message_key="error.database.conflict",
            status_code=409,
            error_code="DATABASE_CONFLICT",
        ) from None


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
        try:
            async with self.transaction():
                await self.repository.clear_current_term()
                return await self.repository.set_current(term)
        except IntegrityError as exc:
            _raise_known_term_conflict(exc)
            raise

    @override
    async def create(
        self,
        obj_in: AcademicTermCreate,
        **kwargs: object,
    ) -> AcademicTerm:
        try:
            async with self.transaction():
                if obj_in.is_current:
                    await self.repository.clear_current_term()
                return await super().create(obj_in, **kwargs)
        except IntegrityError as exc:
            _raise_known_term_conflict(exc)
            raise

    @override
    async def update(
        self,
        db_obj: AcademicTerm,
        obj_in: AcademicTermUpdate,
    ) -> AcademicTerm:
        try:
            return await super().update(db_obj, obj_in)
        except IntegrityError as exc:
            _raise_known_term_conflict(exc)
            raise
