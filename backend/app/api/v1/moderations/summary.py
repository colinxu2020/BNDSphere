from fastapi import APIRouter

from app.api.dependencies import (
    ClubActivityCreateRequestServiceDep,
    ClubActivityUpdateRequestServiceDep,
    ClubUpdateRequestServiceDep,
    UserUpdateRequestServiceDep,
)
from app.schemas.moderations.moderation_common import ModerationPendingSummary

router = APIRouter(tags=["Moderation: Summary"])


@router.get("/summary")
async def get_moderation_pending_summary(
    user_service: UserUpdateRequestServiceDep,
    club_service: ClubUpdateRequestServiceDep,
    activity_create_service: ClubActivityCreateRequestServiceDep,
    activity_update_service: ClubActivityUpdateRequestServiceDep,
) -> ModerationPendingSummary:
    """Pending counts per moderation queue.

    Serves the navigation badge. Without it the frontend has to fetch all four
    moderation lists on every page load and count client-side, because the list
    endpoints take no status filter.

    Authorization comes from the parent router, which is already mounted behind
    RoleChecker([moderator, admin, dev]) — the same policy that guards the queues
    themselves, so this exposes nothing new to anyone.
    """
    user_update_requests = await user_service.count_pending_requests()
    club_update_requests = await club_service.count_pending_requests()
    club_activity_create_requests = (
        await activity_create_service.count_pending_requests()
    )
    club_activity_update_requests = (
        await activity_update_service.count_pending_requests()
    )

    return ModerationPendingSummary(
        user_update_requests=user_update_requests,
        club_update_requests=club_update_requests,
        club_activity_create_requests=club_activity_create_requests,
        club_activity_update_requests=club_activity_update_requests,
        total=(
            user_update_requests
            + club_update_requests
            + club_activity_create_requests
            + club_activity_update_requests
        ),
    )
