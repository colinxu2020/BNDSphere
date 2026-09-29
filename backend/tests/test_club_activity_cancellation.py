from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicTerm, Club, ClubActivity, ClubMember
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum


class TestClubActivityCancellation:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "cancel-president"},
        {"username": "cancel-vice"},
        {"username": "cancel-member"},
        {"username": "cancel-outsider"},
    ]

    @pytest_asyncio.fixture(scope="class")
    async def activities(
        self,
        request: pytest.FixtureRequest,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> dict[str, int]:
        users = request.cls.configured_users
        now = datetime.now(UTC)
        term = AcademicTerm(
            term_name="cancellation-term",
            start_date=now.date() - timedelta(days=5),
            end_date=now.date() + timedelta(days=30),
            is_current=True,
        )
        club = Club(
            name="Cancellation Club",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        db_session.add_all([term, club])
        await db_session.flush()
        for name, membership in (
            ("cancel-president", ClubMembershipEnum.president),
            ("cancel-vice", ClubMembershipEnum.vice_president),
            ("cancel-member", ClubMembershipEnum.member),
        ):
            db_session.add(
                ClubMember(
                    club_id=club.id,
                    user_id=users[name]["user"].id,
                    membership=membership,
                ),
            )
        future = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Future activity",
            description="description",
            location="location",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        started = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Started activity",
            description="description",
            location="location",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        db_session.add_all([future, started])
        await db_session.flush()
        ids = {"club": club.id, "future": future.id, "started": started.id}
        await db_session.commit()
        return ids

    async def test_president_cancels_future_activity_idempotently(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        headers = self.configured_users["cancel-president"]["headers"]
        url = f"/clubs/{activities['club']}/activities/{activities['future']}/cancel"
        first = await client.post(url, headers=headers)
        assert first.status_code == 200, first.text
        cancelled_at = first.json()["cancelled_at"]
        assert cancelled_at is not None
        second = await client.post(url, headers=headers)
        assert second.status_code == 200, second.text
        assert second.json()["cancelled_at"] == cancelled_at

        listing = await client.get(f"/clubs/{activities['club']}/activities/")
        assert listing.status_code == 200
        item = next(
            item
            for item in listing.json()["items"]
            if item["id"] == activities["future"]
        )
        assert item["cancelled_at"] == cancelled_at
