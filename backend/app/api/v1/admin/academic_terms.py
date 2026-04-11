from fastapi import APIRouter
from fastapi_pagination import Page
from starlette.status import HTTP_201_CREATED

from app.api.dependencies import AcademicTermServiceDep
from app.schemas.academic_terms import (
    AcademicTermCreate,
    AcademicTermInfo,
    AcademicTermUpdate,
)
from app.services.errors import AcademicTermNotFoundError

router = APIRouter(tags=["Academic Terms"])


@router.get("/")
async def list_terms(service: AcademicTermServiceDep) -> Page[AcademicTermInfo]:
    return Page[AcademicTermInfo].model_validate(await service.get_multi())


@router.post("/", status_code=HTTP_201_CREATED)
async def create_term(
    term: AcademicTermCreate,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    return AcademicTermInfo.model_validate(await service.create(term))


@router.get("/{term_id}")
async def get_term(term_id: int, service: AcademicTermServiceDep) -> AcademicTermInfo:
    result = await service.get(term_id)
    if result is None:
        raise AcademicTermNotFoundError(term_id)
    return AcademicTermInfo.model_validate(result)


@router.patch("/{term_id}")
async def update_term(
    term_id: int,
    term: AcademicTermUpdate,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise AcademicTermNotFoundError(term_id)
    return AcademicTermInfo.model_validate(await service.update(db_term, term))


@router.delete("/{term_id}")
async def delete_term(
    term_id: int,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise AcademicTermNotFoundError(term_id)
    await service.delete(db_term)
    return AcademicTermInfo.model_validate(db_term)


@router.post("/{term_id}/set-current")
async def set_current_term(
    term_id: int,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise AcademicTermNotFoundError(term_id)
    return AcademicTermInfo.model_validate(await service.set_current(db_term))
