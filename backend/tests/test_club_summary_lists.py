"""Summary list contracts, leadership, and collection-loading regression (#126)."""

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import Club, ClubMember
from app.models.academic_term import AcademicTerm
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.club_activity import ClubActivity
from app.models.clubmember import ClubMembershipEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
)
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum

SUMMARY_FIELDS = {
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


class TestClubSummaryLists:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "summary_admin", "role": "admin"},
        {"username": "summary_president"},
        {"username": "summary_vice"},
        {"username": "summary_member"},
    ]
    configured_users: ClassVar[dict[str, Any]]
    club_ids: ClassVar[dict[str, int]]

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def seed(
        self,
        db_session: AsyncSession,
        setup_class_users: None,
        request: pytest.FixtureRequest,
    ) -> None:
        clubs = [
            Club(
                name=f"Summary {status.value}",
                summary="summary",
                description="description",
                category=ClubCategoryEnum.information_technology,
                status=status,
            )
            for status in ClubStatusEnum
        ]
        db_session.add_all(clubs)
        term = AcademicTerm(
            term_name="Summary term",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 1),
        )
        activity = GeneralActivity(
            name="Summary event",
            description="event",
            level=GeneralActivityLevelEnum.school,
            academic_term=term,
        )
        db_session.add_all([term, activity])
        await db_session.flush()
        request.cls.club_ids = {club.status.value: club.id for club in clubs}
        normal_id = self.club_ids["normal"]
        for username, role in [
            ("summary_president", ClubMembershipEnum.president),
            ("summary_vice", ClubMembershipEnum.vice_president),
            ("summary_member", ClubMembershipEnum.member),
        ]:
            db_session.add(
                ClubMember(
                    club_id=normal_id,
                    user_id=self.configured_users[username]["user"].id,
                    membership=role,
                )
            )
        now = datetime.now(UTC)
        db_session.add(
            ClubActivity(
                name="Summary activity",
                description="activity",
                club_id=normal_id,
                academic_term_id=term.id,
                start_time=now,
                end_time=now + timedelta(hours=1),
                location="school",
            )
        )
        db_session.add_all(
            [
                ClubGeneralActivityRecord(
                    club_id=normal_id,
                    activity_id=activity.id,
                    audit_status=AuditStatusEnum.approved,
                    participation_type="participate_only",
                ),
                StarLevelApplication(club_id=normal_id, academic_term_id=term.id),
            ]
        )
        await db_session.commit()
        db_session.expire_all()

    def admin_headers(self) -> dict[str, str]:
        return self.configured_users["summary_admin"]["headers"]

    @pytest.mark.parametrize("admin", [False, True])
    async def test_list_summary_and_sql(
        self,
        client: AsyncClient,
        db_engine: AsyncEngine,
        db_session: AsyncSession,
        admin: bool,
    ) -> None:
        db_session.expire_all()
        statements: list[tuple[str, object]] = []

        def capture(
            _conn: object,
            _cursor: object,
            statement: str,
            parameters: object,
            *_args: object,
        ) -> None:
            statements.append((statement, parameters))

        event.listen(db_engine.sync_engine, "before_cursor_execute", capture)
        try:
            response = await client.get(
                "/admin/clubs/" if admin else "/clubs/",
                headers=self.admin_headers() if admin else {},
            )
        finally:
            event.remove(db_engine.sync_engine, "before_cursor_execute", capture)
        assert response.status_code == 200
        items = response.json()["items"]
        assert {item["status"] for item in items} == (
            set(self.club_ids) if admin else {"normal"}
        )
        assert all(set(item) == SUMMARY_FIELDS for item in items)
        normal = next(item for item in items if item["status"] == "normal")
        assert normal["president"]["username"] == "summary_president"
        assert set(normal["president"]) == {"id", "username", "avatar_uri", "grade"}
        assert [vp["username"] for vp in normal["vice_presidents"]] == ["summary_vice"]
        assert all(
            item["president"] is None and item["vice_presidents"] == []
            for item in items
            if item["status"] != "normal"
        )
        assert not any(
            "app.club_activities" in stmt or "app.club_general_activity_records" in stmt
            for stmt, _ in statements
        )
        member_reads = [
            (stmt, params)
            for stmt, params in statements
            if "FROM app.club_members" in stmt
        ]
        assert len(member_reads) == 1
        stmt, params = member_reads[0]
        assert "app.club_members.membership IN" in stmt
        encoded = json.dumps(params)
        assert "president" in encoded and "vice_president" in encoded
        assert '"member"' not in encoded

    async def test_filters_and_empty_page(self, client: AsyncClient) -> None:
        response = await client.get(
            "/admin/clubs/",
            headers=self.admin_headers(),
            params={
                "club_status": "archived",
                "category": "information_technology",
                "search": "Summary archived",
            },
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [
            self.club_ids["archived"]
        ]
        response = await client.get("/clubs/", params={"page": 2, "size": 1})
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 1

    @pytest.mark.parametrize("admin", [False, True])
    async def test_detail_keeps_collections(
        self, client: AsyncClient, admin: bool
    ) -> None:
        response = await client.get(
            f"{'/admin' if admin else ''}/clubs/{self.club_ids['normal']}",
            headers=self.admin_headers() if admin else {},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["members"]) == 3
        assert len(body["club_activities"]) == 1
        assert len(body["general_activity_records"]) == 1
        assert "president" not in body

    async def test_admin_patch_keeps_info(self, client: AsyncClient) -> None:
        response = await client.patch(
            f"/admin/clubs/{self.club_ids['normal']}",
            headers=self.admin_headers(),
            json={"summary": "Updated summary"},
        )
        assert response.status_code == 200
        assert response.json()["summary"] == "Updated summary"
        assert {
            "members",
            "club_activities",
            "general_activity_records",
        } <= response.json().keys()

    async def test_star_level_embeds_summary(self, client: AsyncClient) -> None:
        response = await client.get("/star-level/")
        assert response.status_code == 200
        club = response.json()["items"][0]["club"]
        assert set(club) == SUMMARY_FIELDS
        assert club["president"]["username"] == "summary_president"

    async def test_public_club_without_president(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        club = Club(
            name="Unclaimed normal club",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.information_technology,
            status=ClubStatusEnum.normal,
        )
        db_session.add(club)
        await db_session.flush()
        club_id = club.id
        await db_session.commit()
        response = await client.get("/clubs/")
        assert response.status_code == 200
        item = next(item for item in response.json()["items"] if item["id"] == club_id)
        assert item["president"] is None
        assert item["vice_presidents"] == []
