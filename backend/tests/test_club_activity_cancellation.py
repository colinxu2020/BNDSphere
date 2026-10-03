from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicTerm, Club, ClubActivity, ClubMember
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum


class TestClubActivityCancellation:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "cancel-president"},
        {"username": "cancel-vice"},
        {"username": "cancel-member"},
        {"username": "cancel-outsider"},
        {"username": "cancel-moderator", "role": RoleEnum.moderator},
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
        other_club = Club(
            name="Other cancellation club",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        archived_club = Club(
            name="Archived cancellation club",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.archived,
        )
        db_session.add_all([term, club, other_club, archived_club])
        await db_session.flush()
        for extra_club in (other_club, archived_club):
            db_session.add(
                ClubMember(
                    club_id=extra_club.id,
                    user_id=users["cancel-president"]["user"].id,
                    membership=ClubMembershipEnum.president,
                ),
            )
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
        future_update = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Future update activity",
            description="description",
            location="location",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
        )
        future_checkin = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Future check-in activity",
            description="description",
            location="location",
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, hours=1),
        )
        future_auth = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Future authorization activity",
            description="description",
            location="location",
            start_time=now + timedelta(days=4),
            end_time=now + timedelta(days=4, hours=1),
        )
        db_session.add_all(
            [future, started, future_update, future_checkin, future_auth]
        )
        await db_session.flush()
        ids = {
            "club": club.id,
            "other_club": other_club.id,
            "archived_club": archived_club.id,
            "future": future.id,
            "started": started.id,
            "future_update": future_update.id,
            "future_checkin": future_checkin.id,
            "future_auth": future_auth.id,
            "member": users["cancel-member"]["user"].id,
            "vice": users["cancel-vice"]["user"].id,
        }
        await db_session.commit()
        return ids

    async def test_president_cancels_future_activity_idempotently(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        headers = self.configured_users["cancel-president"]["headers"]
        url = f"/clubs/{activities['club']}/activities/{activities['future']}/cancel"
        rating_url = f"/clubs/{activities['club']}/star-rating/"
        before = await client.get(rating_url)
        assert before.status_code == 200, before.text
        assert before.json()["breakdown"]["internal_activities"] == 10
        first = await client.post(url, headers=headers)
        assert first.status_code == 200, first.text
        after = await client.get(rating_url)
        assert after.status_code == 200, after.text
        assert after.json()["breakdown"]["internal_activities"] == 3
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
        detail = await client.get(f"/clubs/{activities['club']}")
        assert detail.status_code == 200
        detail_activity = next(
            item
            for item in detail.json()["club_activities"]
            if item["id"] == activities["future"]
        )
        assert detail_activity["cancelled_at"] == cancelled_at

    async def test_started_activity_cannot_be_cancelled(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        response = await client.post(
            f"/clubs/{activities['club']}/activities/{activities['started']}/cancel",
            headers=self.configured_users["cancel-president"]["headers"],
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "CLUB_ACTIVITY_ALREADY_STARTED"

    async def test_wrong_club_and_archived_club_are_rejected(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        headers = self.configured_users["cancel-president"]["headers"]
        wrong_club = await client.post(
            f"/clubs/{activities['other_club']}/activities/{activities['future_auth']}/cancel",
            headers=headers,
        )
        assert wrong_club.status_code == 404
        assert wrong_club.json()["error_code"] == "CLUB_ACTIVITY_NOT_FOUND"

        archived = await client.post(
            f"/clubs/{activities['archived_club']}/activities/{activities['future_auth']}/cancel",
            headers=headers,
        )
        assert archived.status_code == 403
        assert archived.json()["error_code"] == "CLUB_NOT_ACTIVE"

    async def test_only_leaders_can_cancel(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        url = (
            f"/clubs/{activities['club']}/activities/{activities['future_auth']}/cancel"
        )
        for name in ("cancel-member", "cancel-outsider"):
            response = await client.post(
                url,
                headers=self.configured_users[name]["headers"],
            )
            assert response.status_code == 403
        anonymous = await client.post(url)
        assert anonymous.status_code == 401

        vice = await client.post(
            url,
            headers=self.configured_users["cancel-vice"]["headers"],
        )
        assert vice.status_code == 200, vice.text

    async def test_cancellation_supersedes_pending_update_and_blocks_later_changes(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        president = self.configured_users["cancel-president"]["headers"]
        moderator = self.configured_users["cancel-moderator"]["headers"]
        club_id = activities["club"]
        activity_id = activities["future_update"]
        update_url = f"/clubs/{club_id}/activities/update-requests/{activity_id}"
        request = await client.post(
            update_url,
            json={"name": "Proposed replacement"},
            headers=president,
        )
        assert request.status_code == 200, request.text
        request_id = request.json()["id"]

        cancelled = await client.post(
            f"/clubs/{club_id}/activities/{activity_id}/cancel",
            headers=president,
        )
        assert cancelled.status_code == 200, cancelled.text
        review = await client.patch(
            f"/moderations/club-activities/update-requests/{request_id}",
            json={"moderation_status": "approved"},
            headers=moderator,
        )
        assert review.status_code == 403, review.text
        assert review.json()["error_code"] == "CLUB_ACTIVITY_UPDATE_REQUEST_MODERATED"

        new_request = await client.post(
            update_url,
            json={"name": "Still not allowed"},
            headers=president,
        )
        assert new_request.status_code == 409, new_request.text
        assert new_request.json()["error_code"] == "CLUB_ACTIVITY_CANCELLED"

    async def test_cancellation_keeps_roster_but_rejects_new_check_ins(
        self,
        client: AsyncClient,
        activities: dict[str, int],
    ) -> None:
        president = self.configured_users["cancel-president"]["headers"]
        member_id = activities["member"]
        vice_id = activities["vice"]
        url = f"/clubs/{activities['club']}/activities/{activities['future_checkin']}"
        existing = await client.post(
            f"{url}/check-ins",
            json={"user_ids": [member_id]},
            headers=president,
        )
        assert existing.status_code == 201, existing.text
        assert len(existing.json()) == 1

        cancelled = await client.post(f"{url}/cancel", headers=president)
        assert cancelled.status_code == 200, cancelled.text
        roster = await client.get(f"{url}/check-ins", headers=president)
        assert roster.status_code == 200
        assert [item["user_id"] for item in roster.json()["items"]] == [member_id]

        manual = await client.post(
            f"{url}/check-ins",
            json={"user_ids": [vice_id]},
            headers=president,
        )
        assert manual.status_code == 409, manual.text
        assert manual.json()["error_code"] == "CLUB_ACTIVITY_CANCELLED"

        token = await client.post(f"{url}/check-in-qrcode", headers=president)
        assert token.status_code == 409, token.text
        assert token.json()["error_code"] == "CLUB_ACTIVITY_CANCELLED"

        scan = await client.post(
            f"{url}/check-in-qrcode/scan",
            json={"token": "invalid"},
            headers=self.configured_users["cancel-member"]["headers"],
        )
        assert scan.status_code == 409, scan.text
        assert scan.json()["error_code"] == "CLUB_ACTIVITY_CANCELLED"
