from collections.abc import Sequence
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models.club_activity_check_in import CheckInMethodEnum, ClubActivityCheckIn
from app.repositories.base import RepositoryBase
from app.schemas.club_activity_check_in import ClubActivityCheckInCreate


class ClubActivityCheckInRepository(
    RepositoryBase[
        ClubActivityCheckIn,
        ClubActivityCheckInCreate,
        ClubActivityCheckInCreate,
    ],
):
    model = ClubActivityCheckIn

    async def get_by_activity(
        self,
        club_activity_id: int,
    ) -> Page[ClubActivityCheckIn]:
        stmt = (
            select(ClubActivityCheckIn)
            .where(ClubActivityCheckIn.club_activity_id == club_activity_id)
            # A manual batch commits in one transaction, so checked_in_at's
            # server_default=now() is identical across its rows (now() is
            # transaction-stable in Postgres) — id breaks ties so pagination
            # stays stable instead of arbitrarily splitting/duplicating rows
            # across pages.
            .order_by(
                ClubActivityCheckIn.checked_in_at.asc(),
                ClubActivityCheckIn.id.asc(),
            )
        )
        return cast("Page[ClubActivityCheckIn]", await apaginate(self.db, stmt))

    async def get_checked_in_user_ids(self, club_activity_id: int) -> set[int]:
        stmt = select(ClubActivityCheckIn.user_id).where(
            ClubActivityCheckIn.club_activity_id == club_activity_id,
        )
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def get_by_activity_user(
        self,
        club_activity_id: int,
        user_id: int,
    ) -> ClubActivityCheckIn | None:
        stmt = select(ClubActivityCheckIn).where(
            ClubActivityCheckIn.club_activity_id == club_activity_id,
            ClubActivityCheckIn.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_or_get_existing(
        self,
        club_activity_id: int,
        user_id: int,
        method: CheckInMethodEnum,
        recorded_by_user_id: int,
    ) -> ClubActivityCheckIn:
        stmt = (
            insert(ClubActivityCheckIn)
            .values(
                club_activity_id=club_activity_id,
                user_id=user_id,
                method=method,
                recorded_by_user_id=recorded_by_user_id,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ClubActivityCheckIn.club_activity_id,
                    ClubActivityCheckIn.user_id,
                ],
            )
            .returning(ClubActivityCheckIn)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        if row is not None:
            return row
        existing = await self.get_by_activity_user(club_activity_id, user_id)
        if existing is None:
            raise RuntimeError(
                "check-in insert conflicted but no existing row was found",
            )
        return existing

    async def create_many_ignoring_conflicts(
        self,
        club_activity_id: int,
        user_ids: Sequence[int],
        method: CheckInMethodEnum,
        recorded_by_user_id: int,
    ) -> Sequence[ClubActivityCheckIn]:
        """Insert a whole manual roster as one INSERT (one round trip, one
        transaction — a failure partway can't leave a partially-committed
        roster). Callers must have already deduped ``user_ids`` and filtered
        out ones already checked in; any that still conflict (a concurrent
        request beat this one to it) are silently dropped from the result
        rather than erroring — same idempotent semantics as
        ``create_or_get_existing``, just batched.
        """
        if not user_ids:
            return []
        stmt = (
            insert(ClubActivityCheckIn)
            .values(
                [
                    {
                        "club_activity_id": club_activity_id,
                        "user_id": user_id,
                        "method": method,
                        "recorded_by_user_id": recorded_by_user_id,
                    }
                    for user_id in user_ids
                ],
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ClubActivityCheckIn.club_activity_id,
                    ClubActivityCheckIn.user_id,
                ],
            )
            .returning(ClubActivityCheckIn)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
