"""Shared final club-state check for serialized club-owned writes."""

from app.models.club import Club, ClubStatusEnum
from app.repositories.club import ClubRepository
from app.services.errors import ClubNotFoundError, ResourceForbiddenError


async def get_locked_normal_club(
    repository: ClubRepository,
    club_id: int,
) -> Club:
    """Call inside a transaction, before locking or changing child rows."""
    club = await repository.get_with_lock(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    await repository.db.refresh(club, attribute_names=["status"])
    if club.status != ClubStatusEnum.normal:
        raise ResourceForbiddenError(
            "error.club.not_active",
            "CLUB_NOT_ACTIVE",
            {"club_id": club_id},
        ) from None
    return club
