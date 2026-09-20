"""``GET /users/me/clubs/`` (issue #124): the Summary tier for "my clubs".

Seeds one user with every membership kind across several clubs, plus the
clubs' presidents / vice presidents, then checks the membership filter, the
``president`` (single) / ``vice_presidents`` (list) shape, and that the
endpoint never loads the full member / activity / record collections.

Ids are captured as plain ints in the fixture (see ``test_club_activity_check_in``
for why re-reading them off ORM objects later is unsafe).
"""

from typing import Any, ClassVar, TypedDict

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.main import app
from app.models import Club, ClubMember, User
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum


class ConfiguredUser(TypedDict):
    headers: dict[str, str]
    user: User


class UserClubsFixture(TypedDict):
    club_ids: dict[str, int]
    user_ids: dict[str, int]


def _club(name: str, status: ClubStatusEnum = ClubStatusEnum.normal) -> Club:
    return Club(
        name=name,
        summary=f"{name} summary",
        description=f"{name} description",
        category=ClubCategoryEnum.information_technology,
        status=status,
    )


@pytest_asyncio.fixture(scope="class")
async def setup_user_clubs(
    request: pytest.FixtureRequest,
    db_session: AsyncSession,
    setup_class_users: None,
) -> UserClubsFixture:
    configured_users: dict[str, ConfiguredUser] = request.cls.configured_users
    user_ids = {name: cu["user"].id for name, cu in configured_users.items()}

    clubs = {
        "presiding": _club("My Presiding Club"),
        "vice": _club("My Vice Club", ClubStatusEnum.unreviewed),
        "joined": _club("My Joined Club"),
        "pending": _club("My Pending Club"),
        "left": _club("My Left Club"),
        "unrelated": _club("Unrelated Club"),
    }
    db_session.add_all(clubs.values())
    await db_session.flush()
    club_ids = {key: club.id for key, club in clubs.items()}

    # (club, username, membership) — ``me`` is the user under test; the other
    # rows are the leadership every summary must surface.
    roster = [
        ("presiding", "me", ClubMembershipEnum.president),
        ("presiding", "vp_a", ClubMembershipEnum.vice_president),
        ("presiding", "vp_b", ClubMembershipEnum.vice_president),
        ("presiding", "member", ClubMembershipEnum.member),
        ("vice", "me", ClubMembershipEnum.vice_president),
        ("vice", "president", ClubMembershipEnum.president),
        ("joined", "me", ClubMembershipEnum.member),
        ("joined", "president", ClubMembershipEnum.president),
        ("joined", "vp_a", ClubMembershipEnum.vice_president),
        ("joined", "member", ClubMembershipEnum.left),
        ("pending", "me", ClubMembershipEnum.pending),
        ("left", "me", ClubMembershipEnum.left),
        ("left", "president", ClubMembershipEnum.president),
        ("unrelated", "president", ClubMembershipEnum.president),
    ]
    db_session.add_all(
        ClubMember(
            user_id=user_ids[username],
            club_id=club_ids[club_key],
            membership=membership,
        )
        for club_key, username, membership in roster
    )
    await db_session.flush()

    # Releases the class-level savepoint (see setup_class_users for why this
    # matters), folding the seeded rows into the outer transaction.
    await db_session.commit()
    return {"club_ids": club_ids, "user_ids": user_ids}


class TestUserClubs:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "me", "password": "me-password"},
        {"username": "president", "password": "president-password"},
        {"username": "vp_a", "password": "vp-a-password"},
        {"username": "vp_b", "password": "vp-b-password"},
        {"username": "member", "password": "member-password"},
    ]

    def _headers(self, username: str) -> dict[str, str]:
        return self.configured_users[username]["headers"]

    async def _my_clubs(self, client: AsyncClient) -> dict[int, dict[str, Any]]:
        response = await client.get("/users/me/clubs/", headers=self._headers("me"))
        assert response.status_code == 200
        return {item["club"]["id"]: item for item in response.json()}

    async def test_requires_login(self, client: AsyncClient) -> None:
        response = await client.get("/users/me/clubs/")

        assert response.status_code == 401

    async def test_includes_every_current_membership_but_not_left(
        self,
        client: AsyncClient,
        setup_user_clubs: UserClubsFixture,
    ) -> None:
        club_ids = setup_user_clubs["club_ids"]
        items = await self._my_clubs(client)

        assert {club_id: item["membership"] for club_id, item in items.items()} == {
            club_ids["presiding"]: "president",
            club_ids["vice"]: "vice_president",
            club_ids["joined"]: "member",
            club_ids["pending"]: "pending",
        }
        assert club_ids["left"] not in items
        assert club_ids["unrelated"] not in items

    async def test_summary_shape(
        self,
        client: AsyncClient,
        setup_user_clubs: UserClubsFixture,
    ) -> None:
        club_ids = setup_user_clubs["club_ids"]
        user_ids = setup_user_clubs["user_ids"]
        items = await self._my_clubs(client)

        presiding = items[club_ids["presiding"]]["club"]
        assert set(presiding) == {
            "id",
            "name",
            "category",
            "summary",
            "description",
            "logo_uri",
            "status",
            "star_level",
            "created_at",
            "president",
            "vice_presidents",
        }
        assert presiding["name"] == "My Presiding Club"
        assert presiding["status"] == "normal"
        assert presiding["president"]["id"] == user_ids["me"]
        assert set(presiding["president"]) == {"id", "username", "avatar_uri", "grade"}
        assert {vp["id"] for vp in presiding["vice_presidents"]} == {
            user_ids["vp_a"],
            user_ids["vp_b"],
        }

        vice = items[club_ids["vice"]]["club"]
        assert vice["status"] == "unreviewed"
        assert vice["president"]["id"] == user_ids["president"]
        assert [vp["id"] for vp in vice["vice_presidents"]] == [user_ids["me"]]

        joined = items[club_ids["joined"]]["club"]
        assert joined["president"]["id"] == user_ids["president"]
        assert [vp["id"] for vp in joined["vice_presidents"]] == [user_ids["vp_a"]]

        pending = items[club_ids["pending"]]["club"]
        assert pending["president"] is None
        assert pending["vice_presidents"] == []

    async def test_does_not_load_full_collections(
        self,
        client: AsyncClient,
        db_engine: AsyncEngine,
        setup_user_clubs: UserClubsFixture,
    ) -> None:
        statements: list[str] = []

        def _capture(
            _conn: object,
            _cursor: object,
            statement: str,
            *_args: object,
        ) -> None:
            statements.append(statement)

        event.listen(db_engine.sync_engine, "before_cursor_execute", _capture)
        try:
            await self._my_clubs(client)
        finally:
            event.remove(db_engine.sync_engine, "before_cursor_execute", _capture)

        assert not [s for s in statements if "app.club_activities" in s]
        assert not [s for s in statements if "app.club_general_activity_records" in s]
        # Every club_members read must be a targeted one (filtered by
        # membership), never the whole roster of a club.
        member_reads = [s for s in statements if "FROM app.club_members" in s]
        assert member_reads
        assert all("membership" in s for s in member_reads)
        # Users are read exactly twice: the auth dependency resolving the
        # caller, and one batched read for the leaders — never again for the
        # caller's own membership rows.
        assert len([s for s in statements if "FROM app.users" in s]) == 2

    async def test_managed_endpoint_is_gone(self, client: AsyncClient) -> None:
        assert "/api/v1/clubs/managed/" not in {
            getattr(route, "path", None) for route in app.routes
        }

        response = await client.get(
            "/clubs/managed/",
            headers=self._headers("me"),
            follow_redirects=True,
        )

        # With the route gone, the trailing-slash redirect lands on
        # ``/clubs/{club_id}``, which rejects the non-integer id.
        assert response.status_code == 422
