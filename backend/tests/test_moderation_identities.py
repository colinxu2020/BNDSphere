from datetime import UTC, date, datetime, timedelta
from typing import ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubCategoryEnum
from app.models.club_activity import ClubActivity
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.club_activity import (
    ClubActivityCreateRequest,
    ClubActivityUpdateRequest,
)
from app.models.moderations.user_update_request import UserUpdateRequest
from tests.test_auth import ConfiguredUser

QUEUES = [
    "users/update-requests",
    "clubs/update-requests",
    "club-activities/create-requests",
    "club-activities/update-requests",
]


class TestModerationIdentities:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "identity_applicant"},
        {"username": "identity_reviewer", "role": "admin"},
    ]
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def seed(
        self,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        user_id = self.configured_users["identity_applicant"]["user"].id
        club = Club(
            name="Current club",
            summary="Summary",
            description="Description",
            category=ClubCategoryEnum.information_technology,
        )
        term = AcademicTerm(
            term_name="Identity test",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 1),
        )
        db_session.add_all([club, term])
        await db_session.flush()
        activity_fields = {
            "description": "Description",
            "location": "Room",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC) + timedelta(hours=1),
        }
        activity = ClubActivity(
            name="Current activity",
            club_id=club.id,
            academic_term_id=term.id,
            **activity_fields,
        )
        db_session.add(activity)
        await db_session.flush()
        db_session.add_all(
            [
                UserUpdateRequest(user_id=user_id, username="Proposed username"),
                ClubUpdateRequest(
                    club_id=club.id,
                    requestor_id=user_id,
                    summary="Proposed summary",
                ),
                ClubActivityCreateRequest(
                    club_id=club.id,
                    requestor_id=user_id,
                    name="Proposed creation",
                    **activity_fields,
                ),
                ClubActivityUpdateRequest(
                    club_activity_id=activity.id,
                    requestor_id=user_id,
                    name="Proposed activity",
                    update_fields=["name"],
                ),
            ]
        )
        await db_session.commit()

    @pytest.mark.parametrize("queue", QUEUES)
    async def test_current_identity_is_separate_from_proposed_values(
        self,
        client: AsyncClient,
        queue: str,
    ) -> None:
        response = await client.get(
            f"/moderations/{queue}",
            headers=self.configured_users["identity_reviewer"]["headers"],
        )
        assert response.status_code == 200
        [item] = response.json()["items"]
        assert item.get("requestor_username") == "identity_applicant"
        if queue == "users/update-requests":
            assert item["username"] == "Proposed username"
        elif queue == "club-activities/update-requests":
            assert item.get("club_activity_name") == "Current activity"
            assert item["name"] == "Proposed activity"
        else:
            assert item.get("club_name") == "Current club"

    @pytest.mark.parametrize("queue", QUEUES)
    @pytest.mark.parametrize("authenticated", [False, True])
    async def test_identity_queue_remains_private(
        self,
        client: AsyncClient,
        queue: str,
        *,
        authenticated: bool,
    ) -> None:
        headers = (
            self.configured_users["identity_applicant"]["headers"]
            if authenticated
            else {}
        )
        response = await client.get(f"/moderations/{queue}", headers=headers)
        assert response.status_code == (403 if authenticated else 401)

    @pytest.mark.parametrize(
        "model",
        [
            UserUpdateRequest,
            ClubUpdateRequest,
            ClubActivityCreateRequest,
            ClubActivityUpdateRequest,
        ],
    )
    async def test_labels_load_without_relationship_queries(
        self,
        db_session: AsyncSession,
        model: type,
    ) -> None:
        statements: list[str] = []
        connection = await db_session.connection()

        def record(*args: object) -> None:
            statements.append(str(args[2]))

        event.listen(connection.sync_connection, "before_cursor_execute", record)
        try:
            db_session.expire_all()
            requests = (await db_session.scalars(select(model))).all()
            assert len(requests) == 1
            assert requests[0].requestor_username == "identity_applicant"
            assert len(statements) == 1
        finally:
            event.remove(connection.sync_connection, "before_cursor_execute", record)

    async def test_approval_returns_refreshed_current_username(
        self,
        client: AsyncClient,
    ) -> None:
        headers = self.configured_users["identity_reviewer"]["headers"]
        response = await client.get(
            "/moderations/users/update-requests", headers=headers
        )
        [item] = response.json()["items"]
        response = await client.patch(
            f"/moderations/users/update-requests/{item['id']}",
            headers=headers,
            json={"moderation_status": "approved"},
        )
        assert response.status_code == 200
        assert response.json()["requestor_username"] == "Proposed username"
