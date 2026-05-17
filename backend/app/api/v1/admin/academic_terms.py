from fastapi import APIRouter, status
from fastapi_pagination import Page

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
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
    """List all academic terms, ordered by start date in descending order."""
    return Page[AcademicTermInfo].model_validate(await service.get_multi())


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_term(
    term: AcademicTermCreate,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    """Create a new academic term."""
    return AcademicTermInfo.model_validate(await service.create(term))


@router.get(
    "/{term_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def get_term(term_id: int, service: AcademicTermServiceDep) -> AcademicTermInfo:
    """Get the academic term with the given ID."""
    result = await service.get(term_id)
    if result is None:
        raise AcademicTermNotFoundError(term_id)
    return AcademicTermInfo.model_validate(result)


@router.patch(
    "/{term_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_term(
    term_id: int,
    term: AcademicTermUpdate,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    """Update the academic term with the given ID."""
    db_term = await service.get(term_id)
    if db_term is None:
        raise AcademicTermNotFoundError(term_id)
    return AcademicTermInfo.model_validate(await service.update(db_term, term))


@router.delete(
    "/{term_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def delete_term(
    term_id: int,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    """Delete the academic term with the given ID."""
    db_term = await service.get(term_id)
    if db_term is None:
        raise AcademicTermNotFoundError(term_id)
    await service.delete(db_term)
    return AcademicTermInfo.model_validate(db_term)


@router.post(
    "/{term_id}/set-current",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def set_current_term(
    term_id: int,
    service: AcademicTermServiceDep,
) -> AcademicTermInfo:
    """Set the academic term with the given ID as the current term."""
    db_term = await service.get(term_id)
    if db_term is None:
        raise AcademicTermNotFoundError(term_id)
    return AcademicTermInfo.model_validate(await service.set_current(db_term))
