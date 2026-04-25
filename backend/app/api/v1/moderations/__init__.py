from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.moderations.users import router as users_router
from app.models.user import RoleEnum

router = APIRouter(
    tags=["moderate"],
    dependencies=[
        Depends(RoleChecker([RoleEnum.moderator, RoleEnum.admin, RoleEnum.dev])),
    ],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(users_router, prefix="/users")
