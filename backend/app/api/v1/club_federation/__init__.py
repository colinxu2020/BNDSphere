from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.club_federation.club_general_activities import (
    router as club_general_activity_router,
)
from app.api.v1.club_federation.general_activities import (
    router as general_activity_router,
)
from app.api.v1.club_federation.joint_activities import router as joint_activity_router
from app.api.v1.club_federation.star_level import router as star_level_router
from app.models.user import RoleEnum

router = APIRouter(
    dependencies=[
        Depends(RoleChecker([RoleEnum.dev, RoleEnum.admin, RoleEnum.federation_staff])),
    ],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(general_activity_router, prefix="/general-activity")
router.include_router(
    club_general_activity_router,
    prefix="/general-activity/club-records",
)
router.include_router(star_level_router, prefix="/star-level")
router.include_router(joint_activity_router, prefix="/joint-activities")
