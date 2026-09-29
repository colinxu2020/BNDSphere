"""Archiving a club preserves history without leaving member-facing access."""

from typing import ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Club, ClubMember
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum


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
        ids = {name: club.id for name, club in clubs.items()}
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
