from fastapi import APIRouter, HTTPException
from fastapi_pagination import Page

from app.api.dependencies import AcademicTermServiceDep
from app.models import AcademicTerm
from app.schemas.academic_terms import (
    AcademicTermCreate,
    AcademicTermInfo,
    AcademicTermUpdate,
)

router = APIRouter(tags=["Academic Terms"])


@router.get("/", response_model=Page[AcademicTermInfo])
async def list_terms(service: AcademicTermServiceDep) -> Page[AcademicTerm]:
    return await service.get_multi()


@router.post("/")
async def create_term(
    term: AcademicTermCreate,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    return AcademicTermInfo.model_validate(await service.create(term))


@router.get("/{term_id}")
async def get_term(term_id: int, service: AcademicTermServiceDep) -> AcademicTermInfo:
    result = await service.get(term_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return AcademicTermInfo.model_validate(result)


@router.patch("/{term_id}")
async def update_term(
    term_id: int,
    term: AcademicTermUpdate,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return AcademicTermInfo.model_validate(await service.update(db_term, term))


@router.delete("/{term_id}")
async def delete_term(
    term_id: int,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    await service.delete(db_term)
    return AcademicTermInfo.model_validate(db_term)


@router.post("/{term_id}/set-current")
async def set_current_term(
    term_id: int,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return AcademicTermInfo.model_validate(await service.set_current(db_term))
