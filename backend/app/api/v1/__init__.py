from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.announcements import router as announcements_router
from app.api.v1.auth import router as auth_router
from app.api.v1.club_activities import router as club_activities_router
from app.api.v1.club_federation import router as club_federation_router
from app.api.v1.club_general_activities import router as club_general_activities_router
from app.api.v1.club_joint_activities import router as club_joint_activities_router
from app.api.v1.club_star_level import router as club_star_level_router
from app.api.v1.clubs import router as clubs_router
from app.api.v1.general_activities import router as general_activities_router
from app.api.v1.joint_activities import router as joint_activities_router
from app.api.v1.moderations import router as moderation_router
from app.api.v1.star_level import router as star_level_router
from app.api.v1.star_rating import router as star_rating_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as users_router
from app.api.v1.verifications import router as verification_router

router = APIRouter()
router.include_router(users_router, prefix="/users")
router.include_router(auth_router, prefix="/auth")
router.include_router(clubs_router, prefix="/clubs")
router.include_router(club_activities_router, prefix="/clubs/{club_id}/activities")
router.include_router(admin_router, prefix="/admin")
router.include_router(general_activities_router, prefix="/general-activities")
router.include_router(joint_activities_router, prefix="/joint-activities")
router.include_router(
    club_joint_activities_router,
    prefix="/clubs/{club_id}/joint-activities",
)
router.include_router(
    club_general_activities_router,
    prefix="/clubs/{club_id}/general-activities",
)
router.include_router(
    club_star_level_router,
    prefix="/clubs/{club_id}/star-level",
)
router.include_router(
    star_rating_router,
    prefix="/clubs/{club_id}/star-rating",
)
router.include_router(
    star_level_router,
    prefix="/star-level",
)
router.include_router(club_federation_router, prefix="/club-federation")
router.include_router(moderation_router, prefix="/moderations")
router.include_router(verification_router, prefix="/clubs/{club_id}")
router.include_router(uploads_router, prefix="/uploads")
router.include_router(announcements_router, prefix="/announcements")
