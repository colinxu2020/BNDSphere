from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.admin.academic_terms import router as academic_terms_router
from app.api.v1.admin.clubs import router as clubs_router
from app.api.v1.admin.users import router as users_router
from app.models.user import RoleEnum

router = APIRouter(
    dependencies=[Depends(RoleChecker([RoleEnum.dev, RoleEnum.admin]))],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(users_router, prefix="/users")
router.include_router(clubs_router, prefix="/clubs")
router.include_router(academic_terms_router, prefix="/academic-terms")
