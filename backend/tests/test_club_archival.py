"""Archiving a club preserves history without leaving member-facing access."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicTerm, Club, ClubActivity, ClubActivityCheckIn, ClubMember
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.club_activity_check_in import CheckInMethodEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum
from app.models.verifications.club_membership import ClubMembershipRequest


class TestClubArchival:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "archive-president"},
        {"username": "archive-vice"},
        {"username": "archive-member"},
        {"username": "archive-other-president"},
        {"username": "archive-admin", "role": RoleEnum.admin},
    ]

    @pytest_asyncio.fixture(scope="class")
    async def clubs(
        self,
        request: pytest.FixtureRequest,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> dict[str, int]:
        users = request.cls.configured_users
        clubs = {
            name: Club(
                name=f"Archival {name}",
                summary="summary",
                description="description",
                category=ClubCategoryEnum.natural_science,
                status=status,
            )
            for name, status in (
                ("normal", ClubStatusEnum.normal),
                ("permissions", ClubStatusEnum.normal),
                ("admin_patch", ClubStatusEnum.normal),
                ("unreviewed", ClubStatusEnum.unreviewed),
                ("archived", ClubStatusEnum.archived),
                ("other", ClubStatusEnum.normal),
            )
        }
        db_session.add_all(clubs.values())
        await db_session.flush()
        for club_name in (
            "normal",
            "permissions",
            "admin_patch",
            "unreviewed",
            "archived",
        ):
            for username, membership in (
                ("archive-president", ClubMembershipEnum.president),
                ("archive-vice", ClubMembershipEnum.vice_president),
                ("archive-member", ClubMembershipEnum.member),
            ):
                db_session.add(
                    ClubMember(
                        club_id=clubs[club_name].id,
                        user_id=users[username]["user"].id,
                        membership=membership,
                    ),
                )
        db_session.add(
            ClubMember(
                club_id=clubs["other"].id,
                user_id=users["archive-other-president"]["user"].id,
                membership=ClubMembershipEnum.president,
            ),
        )
        now = datetime.now(UTC)
        term = AcademicTerm(
            term_name="archival-read-term",
            start_date=now.date() - timedelta(days=1),
            end_date=now.date() + timedelta(days=30),
        )
        db_session.add(term)
        await db_session.flush()
        activity = ClubActivity(
            club_id=clubs["archived"].id,
            academic_term_id=term.id,
            name="Preserved archived activity",
            description="history",
            location="room",
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
        )
        db_session.add(activity)
        await db_session.flush()
        db_session.add_all(
            [
                ClubActivityCheckIn(
                    club_activity_id=activity.id,
                    user_id=users["archive-member"]["user"].id,
                    recorded_by_user_id=users["archive-president"]["user"].id,
                    method=CheckInMethodEnum.manual,
                ),
                ClubMembershipRequest(
                    club_id=clubs["archived"].id,
                    applicant_id=users["archive-other-president"]["user"].id,
                    message="old request",
                ),
            ],
        )
        ids = {name: club.id for name, club in clubs.items()}
        ids["archived_activity"] = activity.id
        await db_session.commit()
        return ids

    def _headers(self, username: str) -> dict[str, str]:
        return self.configured_users[username]["headers"]

    async def test_president_archives_once_and_retries_without_a_body(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        clubs: dict[str, int],
    ) -> None:
        club_id = clubs["normal"]
        url = f"/clubs/{club_id}/archive"
        first = await client.post(url, headers=self._headers("archive-president"))
        assert first.status_code == 204, first.text
        assert first.content == b""
        second = await client.post(url, headers=self._headers("archive-president"))
        assert second.status_code == 204, second.text
        assert second.content == b""
        club = await db_session.get(Club, club_id)
        assert club is not None
        await db_session.refresh(club)
        assert club.status == ClubStatusEnum.archived

    async def test_only_president_or_admin_can_archive(
        self,
        client: AsyncClient,
        clubs: dict[str, int],
    ) -> None:
        url = f"/clubs/{clubs['permissions']}/archive"
        for username in ("archive-vice", "archive-member", "archive-other-president"):
            response = await client.post(url, headers=self._headers(username))
            assert response.status_code == 403, response.text
        assert (await client.post(url)).status_code == 401
        admin = await client.post(url, headers=self._headers("archive-admin"))
        assert admin.status_code == 204, admin.text

    async def test_unreviewed_and_missing_clubs_are_not_archivable(
        self,
        client: AsyncClient,
        clubs: dict[str, int],
    ) -> None:
        unreviewed = await client.post(
            f"/clubs/{clubs['unreviewed']}/archive",
            headers=self._headers("archive-president"),
        )
        assert unreviewed.status_code == 403, unreviewed.text
        assert unreviewed.json()["error_code"] == "CLUB_NOT_ACTIVE"

        missing = await client.post(
            "/clubs/99999999/archive",
            headers=self._headers("archive-president"),
        )
        assert missing.status_code == 404, missing.text
        assert missing.json()["error_code"] == "CLUB_NOT_FOUND"

    async def test_admin_patch_cannot_archive_or_resurrect(
        self,
        client: AsyncClient,
        clubs: dict[str, int],
    ) -> None:
        headers = self._headers("archive-admin")
        bypass = await client.patch(
            f"/admin/clubs/{clubs['admin_patch']}",
            json={"status": "archived"},
            headers=headers,
        )
        assert bypass.status_code == 409, bypass.text

        for payload in ({"status": "normal"}, {"summary": "not read-only"}):
            change = await client.patch(
                f"/admin/clubs/{clubs['archived']}",
                json=payload,
                headers=headers,
            )
            assert change.status_code == 403, change.text
            assert change.json()["error_code"] == "CLUB_NOT_ACTIVE"

    async def test_archived_history_is_hidden_from_public_and_members(
        self,
        client: AsyncClient,
        clubs: dict[str, int],
    ) -> None:
        club_id = clubs["archived"]
        for url in (
            f"/clubs/{club_id}",
            f"/clubs/{club_id}/activities/",
            f"/clubs/{club_id}/activities/refs/",
            f"/clubs/{club_id}/star-rating/",
        ):
            response = await client.get(url)
            assert response.status_code in {403, 404}, (url, response.text)

        listing = await client.get("/clubs/", params={"size": 100})
        refs = await client.get("/clubs/refs/", params={"size": 100})
        assert club_id not in {item["id"] for item in listing.json()["items"]}
        assert club_id not in {item["id"] for item in refs.json()["items"]}

        for username in ("archive-president", "archive-other-president"):
            mine = await client.get("/users/me/clubs/", headers=self._headers(username))
            assert mine.status_code == 200
            assert club_id not in {item["club"]["id"] for item in mine.json()}

        for url in (
            f"/clubs/{club_id}/manage",
            f"/clubs/{club_id}/activities/{clubs['archived_activity']}/check-ins",
            f"/clubs/{club_id}/membership-requests",
        ):
            response = await client.get(url, headers=self._headers("archive-president"))
            assert response.status_code in {403, 404}, (url, response.text)

    async def test_admin_can_read_archived_history_without_mutating_it(
        self,
        client: AsyncClient,
        clubs: dict[str, int],
    ) -> None:
        headers = self._headers("archive-admin")
        detail = await client.get(f"/admin/clubs/{clubs['archived']}", headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["status"] == "archived"
        assert [item["id"] for item in detail.json()["club_activities"]] == [
            clubs["archived_activity"],
        ]
        roster = await client.get(
            f"/clubs/{clubs['archived']}/activities/{clubs['archived_activity']}/check-ins",
            headers=headers,
        )
        assert roster.status_code == 200, roster.text
        assert len(roster.json()["items"]) == 1
