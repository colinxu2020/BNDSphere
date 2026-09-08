from datetime import UTC, datetime

from fastapi_pagination import Page

from app.core.security import create_check_in_token, verify_check_in_token
from app.models.club_activity import ClubActivity
from app.models.club_activity_check_in import CheckInMethodEnum, ClubActivityCheckIn
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.repositories.club import ClubMemberRepository
from app.repositories.club_activity import ClubActivityRepository
from app.repositories.club_activity_check_in import ClubActivityCheckInRepository
from app.schemas.club_activity_check_in import ClubActivityCheckInCreate
from app.services.base import ServiceBase
from app.services.errors import (
    ClubActivityCheckInInvalidTokenError,
    ClubActivityCheckInNotInProgressError,
    ClubActivityCheckInNotMemberError,
    ClubActivityNotFoundError,
)

_ACTIVE_MEMBERSHIPS = frozenset(
    {
        ClubMembershipEnum.member,
        ClubMembershipEnum.president,
        ClubMembershipEnum.vice_president,
    },
)


class ClubActivityCheckInService(
    ServiceBase[
        ClubActivityCheckIn,
        ClubActivityCheckInCreate,
        ClubActivityCheckInCreate,
    ],
):
    repository: ClubActivityCheckInRepository

    def __init__(
        self,
        repository: ClubActivityCheckInRepository,
        activity_repository: ClubActivityRepository | None = None,
        member_repository: ClubMemberRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.activity_repository = activity_repository or ClubActivityRepository(
            repository.db,
        )
        self.member_repository = member_repository or ClubMemberRepository(
            repository.db,
        )

    async def get_check_ins(
        self,
        club_id: int,
        activity_id: int,
    ) -> Page[ClubActivityCheckIn]:
        activity = await self._get_club_activity(club_id, activity_id)
        return await self.repository.get_by_activity(activity.id)

    async def check_in_manual(
        self,
        club_id: int,
        activity_id: int,
        user_ids: list[int],
        recorder: User,
    ) -> list[ClubActivityCheckIn]:
        """(President/vice-president) record members who attended, after the
        fact. Idempotent — user ids already checked in are silently skipped
        rather than erroring, so the roster can be resubmitted freely.
        """
        async with self.transaction():
            activity = await self._get_club_activity(club_id, activity_id)
            for user_id in user_ids:
                await self._ensure_active_member(club_id, user_id)

            already_checked_in = await self.repository.get_checked_in_user_ids(
                activity.id,
            )
            new_user_ids = dict.fromkeys(
                user_id for user_id in user_ids if user_id not in already_checked_in
            )

            return [
                await self.repository.create(
                    ClubActivityCheckInCreate(
                        club_activity_id=activity.id,
                        user_id=user_id,
                        method=CheckInMethodEnum.manual,
                        recorded_by_user_id=recorder.id,
                    ),
                )
                for user_id in new_user_ids
            ]

    async def generate_qr_token(
        self,
        club_id: int,
        activity_id: int,
    ) -> tuple[str, datetime]:
        """(President/vice-president) mint a check-in token for the QR code,
        valid only while the activity is in progress — it expires at the
        activity's end time regardless of when it was generated.
        """
        activity = await self._get_club_activity(club_id, activity_id)
        self._ensure_activity_in_progress(activity)
        expires_at = activity.end_time
        return create_check_in_token(activity.id, expires_at), expires_at

    async def check_in_via_qr(
        self,
        club_id: int,
        activity_id: int,
        token: str,
        user: User,
    ) -> ClubActivityCheckIn:
        """Self check-in by scanning the activity's QR code. Idempotent — a
        second scan by the same user returns the existing row rather than
        erroring.
        """
        activity = await self._get_club_activity(club_id, activity_id)
        self._ensure_activity_in_progress(activity)

        try:
            payload = verify_check_in_token(token)
        except ValueError:
            raise ClubActivityCheckInInvalidTokenError from None
        if payload.get("activity_id") != activity.id:
            raise ClubActivityCheckInInvalidTokenError from None

        await self._ensure_active_member(club_id, user.id)

        async with self.transaction():
            existing = await self.repository.get_by_activity_user(
                activity.id,
                user.id,
            )
            if existing is not None:
                return existing
            return await self.repository.create(
                ClubActivityCheckInCreate(
                    club_activity_id=activity.id,
                    user_id=user.id,
                    method=CheckInMethodEnum.qrcode,
                    recorded_by_user_id=user.id,
                ),
            )

    async def _get_club_activity(self, club_id: int, activity_id: int) -> ClubActivity:
        activity = await self.activity_repository.get(activity_id)
        if activity is None or activity.club_id != club_id:
            raise ClubActivityNotFoundError(activity_id) from None
        return activity

    def _ensure_activity_in_progress(self, activity: ClubActivity) -> None:
        now = datetime.now(UTC)
        if now < activity.start_time or now > activity.end_time:
            raise ClubActivityCheckInNotInProgressError(activity.id) from None

    async def _ensure_active_member(self, club_id: int, user_id: int) -> None:
        member = await self.member_repository.get_by_club_user_id(club_id, user_id)
        if member is None or member.membership not in _ACTIVE_MEMBERSHIPS:
            raise ClubActivityCheckInNotMemberError(user_id) from None
