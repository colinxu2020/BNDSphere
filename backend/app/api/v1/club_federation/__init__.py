from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.club_federation.club_general_activities import (
    router as club_general_activity_router,
)
from app.api.v1.club_federation.general_activities import (
    router as general_activity_router,
)
from app.models.user import RoleEnum

router = APIRouter(
    tags=["Club Federation", "admin"],
    dependencies=[Depends(RoleChecker([RoleEnum.dev, RoleEnum.admin, RoleEnum.scf]))],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(general_activity_router, prefix="/general-activity")
router.include_router(
    club_general_activity_router,
    prefix="/general-activity/club-records",
)
