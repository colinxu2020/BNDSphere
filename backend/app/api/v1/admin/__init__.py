from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.admin.academic_terms import router as academic_terms_router
from app.models.user import RoleEnum

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(RoleChecker([RoleEnum.dev, RoleEnum.admin]))],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(academic_terms_router, prefix="/academic_terms")
