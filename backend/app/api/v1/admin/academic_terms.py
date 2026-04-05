from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import ServiceFactory
from app.schemas.academic_terms import (
    AcademicTermCreate,
    AcademicTermInfo,
    AcademicTermUpdate,
)
from app.services.academic_term import AcademicTermService

router = APIRouter(tags=["Academic Terms"])
ServiceDep = Annotated[
    AcademicTermService,
    Depends(ServiceFactory(AcademicTermService)),
]


@router.get("/")
async def list_terms(service: ServiceDep) -> list[AcademicTermInfo]:
    return [AcademicTermInfo.model_validate(x) for x in await service.get_muli()]


@router.post("/")
async def create_term(
    term: AcademicTermCreate,
    service: ServiceDep,
) -> AcademicTermInfo:
    return AcademicTermInfo.model_validate(await service.create(term))


@router.get("/{term_id}")
async def get_term(term_id: int, service: ServiceDep) -> AcademicTermInfo:
    result = await service.get(term_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return AcademicTermInfo.model_validate(result)


@router.patch("/{term_id}")
async def update_term(
    term_id: int,
    term: AcademicTermUpdate,
    service: ServiceDep,
) -> AcademicTermInfo:
    db_term = await service.get(term_id)
    if db_term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return AcademicTermInfo.model_validate(await service.update(db_term, term))
