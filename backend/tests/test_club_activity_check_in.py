"""Club activity check-in (issue #72): manual roster + QR self-check-in.

``setup_activity`` builds on ``setup_class_users`` (see ``conftest.py``) by
seeding a club, its membership roster, and a couple of activities directly
through the ORM — there's no API for creating an already-approved club
activity (creation is moderation-gated), so going through the DB session is
the only way to get a fixture in place without also exercising the
moderation flow.

Every value the tests use is captured as a plain int in the fixture itself,
never re-read off an ORM object later: a test that exercises an error path
rolls the shared class-scoped session back to a savepoint, which expires
every object loaded in it, including ones held by other tests via
``configured_users``/``setup_activity`` — a later ``.id`` access on such an
object would need a lazy DB round trip outside of an awaited context and
crash with ``MissingGreenlet``.
"""

from datetime import UTC, datetime, timedelta
from typing import ClassVar, TypedDict

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_check_in_token
from app.models import AcademicTerm, Club, ClubActivity, ClubMember, User
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum


class ConfiguredUser(TypedDict):
    headers: dict[str, str]
    user: User


class ActivityFixture(TypedDict):
    club_id: int
    active_activity_id: int
    active_activity_2_id: int
    upcoming_activity_id: int
    archived_club_id: int
    archived_club_activity_id: int
    user_ids: dict[str, int]


@pytest_asyncio.fixture(scope="class")
async def setup_activity(
    request: pytest.FixtureRequest,
    db_session: AsyncSession,
    setup_class_users: None,
) -> ActivityFixture:
    configured_users: dict[str, ConfiguredUser] = request.cls.configured_users
    user_ids = {name: cu["user"].id for name, cu in configured_users.items()}

    term = AcademicTerm(
        term_name="check-in-test-term",
        start_date=datetime.now(UTC).date() - timedelta(days=30),
        end_date=datetime.now(UTC).date() + timedelta(days=180),
        is_current=True,
    )
    db_session.add(term)
    await db_session.flush()

    club = Club(
        name="Check-in Test Club",
        summary="summary",
        description="description",
        status=ClubStatusEnum.normal,
        category=ClubCategoryEnum.other,
    )
    db_session.add(club)
    await db_session.flush()

    for username, membership in (
        ("president", ClubMembershipEnum.president),
        ("vice_president", ClubMembershipEnum.vice_president),
        ("member", ClubMembershipEnum.member),
        ("left_member", ClubMembershipEnum.left),
        ("departing_member", ClubMembershipEnum.member),
    ):
        db_session.add(
            ClubMember(
                user_id=user_ids[username],
                club_id=club.id,
                membership=membership,
            ),
        )
    await db_session.flush()

    now = datetime.now(UTC)
    active_activity = ClubActivity(
        name="Active activity",
        description="description",
        club_id=club.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        location="location",
        academic_term_id=term.id,
    )
    active_activity_2 = ClubActivity(
        name="Active activity 2",
        description="description",
        club_id=club.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        location="location",
        academic_term_id=term.id,
    )
    upcoming_activity = ClubActivity(
        name="Upcoming activity",
        description="description",
        club_id=club.id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        location="location",
        academic_term_id=term.id,
    )
    db_session.add_all([active_activity, active_activity_2, upcoming_activity])
    await db_session.flush()

    # A second, archived club — same president — to check that check-in
    # write paths reject it the same way other club-scoped mutations do.
    archived_club = Club(
        name="Archived Check-in Test Club",
        summary="summary",
        description="description",
        status=ClubStatusEnum.archived,
        category=ClubCategoryEnum.other,
    )
    db_session.add(archived_club)
    await db_session.flush()
    db_session.add(
        ClubMember(
            user_id=user_ids["president"],
            club_id=archived_club.id,
            membership=ClubMembershipEnum.president,
        ),
    )
    archived_club_activity = ClubActivity(
        name="Archived club's activity",
        description="description",
        club_id=archived_club.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        location="location",
        academic_term_id=term.id,
    )
    db_session.add(archived_club_activity)
    await db_session.flush()

    fixture: ActivityFixture = {
        "club_id": club.id,
        "active_activity_id": active_activity.id,
        "active_activity_2_id": active_activity_2.id,
        "upcoming_activity_id": upcoming_activity.id,
        "archived_club_id": archived_club.id,
        "archived_club_activity_id": archived_club_activity.id,
        "user_ids": user_ids,
    }

    # Releases the class-level savepoint (see setup_class_users for why this
    # matters), folding the seeded rows into the outer transaction.
    await db_session.commit()
    return fixture


class TestClubActivityCheckIn:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "president", "password": "president-password"},
        {"username": "vice_president", "password": "vice-president-password"},
        {"username": "member", "password": "member-password"},
        {"username": "left_member", "password": "left-member-password"},
        {"username": "outsider", "password": "outsider-password"},
        {"username": "departing_member", "password": "departing-member-password"},
    ]

    def _url(self, club_id: int, activity_id: int, suffix: str) -> str:
        return f"/clubs/{club_id}/activities/{activity_id}/{suffix}"

    def _headers(self, username: str) -> dict[str, str]:
        return self.configured_users[username]["headers"]

    # ── manual check-in ──────────────────────────────────────────────

    async def test_manual_check_in_by_president_succeeds(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_id"]
        member_id = setup_activity["user_ids"]["member"]
        president_id = setup_activity["user_ids"]["president"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [member_id]},
            headers=self._headers("president"),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body) == 1
        assert body[0]["user_id"] == member_id
        assert body[0]["method"] == "manual"
        assert body[0]["recorded_by_user_id"] == president_id

        # Resubmitting the same roster is a no-op, not a duplicate error.
        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [member_id]},
            headers=self._headers("president"),
        )
        assert resp.status_code == 201
        assert resp.json() == []

        listing = await client.get(
            self._url(club_id, activity_id, "check-ins"),
            headers=self._headers("president"),
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

    async def test_manual_check_in_forbidden_for_regular_member(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_2_id"]
        member_id = setup_activity["user_ids"]["member"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [member_id]},
            headers=self._headers("member"),
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "CLUB_ROLE_NOT_ALLOWED"

    async def test_manual_check_in_rejects_non_member(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_2_id"]
        outsider_id = setup_activity["user_ids"]["outsider"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [outsider_id]},
            headers=self._headers("president"),
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_code"] == "CLUB_ACTIVITY_CHECK_IN_NOT_MEMBER"
        assert body["details"] == {"user_id": outsider_id}

    async def test_manual_check_in_rejects_left_member(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_2_id"]
        left_member_id = setup_activity["user_ids"]["left_member"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [left_member_id]},
            headers=self._headers("vice_president"),
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "CLUB_ACTIVITY_CHECK_IN_NOT_MEMBER"

    async def test_manual_check_in_rejects_archived_club(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        # ClubRoleChecker itself doesn't check club status (archived clubs
        # keep their membership rows, see business_process.md), so this
        # exercises the service-level _ensure_club_normal check instead.
        club_id = setup_activity["archived_club_id"]
        activity_id = setup_activity["archived_club_activity_id"]
        president_id = setup_activity["user_ids"]["president"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [president_id]},
            headers=self._headers("president"),
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "CLUB_NOT_ACTIVE"

    async def test_manual_check_in_resubmission_skips_departed_member(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_activity: ActivityFixture,
    ) -> None:
        """Regression: resubmitting the full roster (the documented way to
        add newly-attended members) must not fail just because someone
        checked in earlier has since left the club — membership is only
        validated for ids that aren't already checked in."""
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_2_id"]
        departing_member_id = setup_activity["user_ids"]["departing_member"]
        vice_president_id = setup_activity["user_ids"]["vice_president"]

        first = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [departing_member_id]},
            headers=self._headers("president"),
        )
        assert first.status_code == 201
        assert len(first.json()) == 1

        await db_session.execute(
            update(ClubMember)
            .where(
                ClubMember.club_id == club_id,
                ClubMember.user_id == departing_member_id,
            )
            .values(membership=ClubMembershipEnum.left),
        )
        await db_session.commit()

        resp = await client.post(
            self._url(club_id, activity_id, "check-ins"),
            json={"user_ids": [departing_member_id, vice_president_id]},
            headers=self._headers("president"),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body) == 1
        assert body[0]["user_id"] == vice_president_id

    async def test_get_check_ins_forbidden_for_regular_member(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_id"]

        resp = await client.get(
            self._url(club_id, activity_id, "check-ins"),
            headers=self._headers("member"),
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "CLUB_ROLE_NOT_ALLOWED"

    # ── QR self-check-in ─────────────────────────────────────────────

    async def test_generate_qr_rejects_activity_not_in_progress(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["upcoming_activity_id"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode"),
            headers=self._headers("president"),
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "CLUB_ACTIVITY_CHECK_IN_NOT_IN_PROGRESS"

    async def test_qr_scan_success_and_idempotent(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_2_id"]
        member_id = setup_activity["user_ids"]["member"]

        gen = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode"),
            headers=self._headers("president"),
        )
        assert gen.status_code == 200
        token = gen.json()["token"]

        first = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode/scan"),
            json={"token": token},
            headers=self._headers("member"),
        )
        assert first.status_code == 201
        first_body = first.json()
        assert first_body["method"] == "qrcode"
        assert first_body["user_id"] == member_id
        assert first_body["recorded_by_user_id"] == member_id

        # Scanning again returns the same row rather than erroring.
        second = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode/scan"),
            json={"token": token},
            headers=self._headers("member"),
        )
        assert second.status_code == 201
        assert second.json()["id"] == first_body["id"]

    async def test_qr_scan_rejects_outsider(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_id"]

        gen = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode"),
            headers=self._headers("president"),
        )
        token = gen.json()["token"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode/scan"),
            json={"token": token},
            headers=self._headers("outsider"),
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "CLUB_ACTIVITY_CHECK_IN_NOT_MEMBER"

    async def test_qr_scan_rejects_invalid_token(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_id"]

        resp = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode/scan"),
            json={"token": "not-a-real-token"},
            headers=self._headers("member"),
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "CLUB_ACTIVITY_CHECK_IN_INVALID_TOKEN"

    async def test_qr_scan_rejects_token_for_another_activity(
        self,
        client: AsyncClient,
        setup_activity: ActivityFixture,
    ) -> None:
        club_id = setup_activity["club_id"]
        activity_id = setup_activity["active_activity_id"]
        other_activity_id = setup_activity["active_activity_2_id"]

        token = create_check_in_token(
            other_activity_id,
            datetime.now(UTC) + timedelta(hours=1),
        )

        resp = await client.post(
            self._url(club_id, activity_id, "check-in-qrcode/scan"),
            json={"token": token},
            headers=self._headers("member"),
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "CLUB_ACTIVITY_CHECK_IN_INVALID_TOKEN"
