from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.dev.deployment import router as deployment_router
from app.models.user import RoleEnum

# dev only, deliberately excluding admin: managing users and clubs must not
# confer the ability to restart containers on the host.
router = APIRouter(
    dependencies=[Depends(RoleChecker([RoleEnum.dev]))],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(deployment_router, prefix="/deployment")
