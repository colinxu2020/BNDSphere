from fastapi import APIRouter, Depends

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import RoleChecker
from app.api.v1.moderations.club_activities import router as club_activities_router
from app.api.v1.moderations.clubs import router as clubs_router
from app.api.v1.moderations.summary import router as summary_router
from app.api.v1.moderations.users import router as users_router
from app.models.user import RoleEnum

router = APIRouter(
    dependencies=[
        Depends(RoleChecker([RoleEnum.moderator, RoleEnum.admin, RoleEnum.dev])),
    ],
    responses=PERMISSION_DENIED_RESPONSE | TOKEN_INVALID_RESPONSE,
)
router.include_router(users_router, prefix="/users")
router.include_router(club_activities_router, prefix="/club-activities")
router.include_router(clubs_router, prefix="/clubs")
# No prefix: the summary spans every queue, so it sits at /moderations/summary.
router.include_router(summary_router)
