from typing import ClassVar
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import RoleEnum


class TestClubUpdateRequestModeration:
    """Club profile update requests must validate the same way on creation and
    on approval, and approval must never surface a raw 500."""

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {"username": "pres_approval", "password": "pw12345678"},
        {
            "username": "mod_approval",
            "password": "pw12345678",
            "role": RoleEnum.moderator,
        },
    ]

    async def _make_club(
        self,
        db_session: AsyncSession,
    ) -> Club:
        users = self.configured_users
        # Earlier tests may roll back a savepoint and expire this ORM instance;
        # reload it so ``.id`` doesn't trigger sync lazy IO outside a greenlet.
        president = users["pres_approval"]["user"]
        await db_session.refresh(president)
        club = Club(
            name=f"ApprovalClub-{uuid4().hex[:12]}",
            summary="s",
            description="d",
            category=ClubCategoryEnum.other,
            status=ClubStatusEnum.normal,
        )
        db_session.add(club)
        await db_session.flush()
        db_session.add(
            ClubMember(
                club_id=club.id,
                user_id=president.id,
                membership=ClubMembershipEnum.president,
            ),
        )
        await db_session.flush()
        return club

    async def test_create_rejects_overlong_summary(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        club = await self._make_club(db_session)
        resp = await client.post(
            f"/clubs/{club.id}/update-requests",
            headers=self.configured_users["pres_approval"]["headers"],
            json={"summary": "X" * 51},
        )
        assert resp.status_code == 422, resp.text

    async def test_create_rejects_overlong_description(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        club = await self._make_club(db_session)
        resp = await client.post(
            f"/clubs/{club.id}/update-requests",
            headers=self.configured_users["pres_approval"]["headers"],
            json={"description": "D" * 401},
        )
        assert resp.status_code == 422, resp.text

    async def test_create_then_approve_applies_changes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        club = await self._make_club(db_session)
        created = await client.post(
            f"/clubs/{club.id}/update-requests",
            headers=self.configured_users["pres_approval"]["headers"],
            json={"summary": "new summary", "description": "new description"},
        )
        assert created.status_code == 200, created.text

        approved = await client.patch(
            f"/moderations/clubs/update-requests/{created.json()['id']}",
            headers=self.configured_users["mod_approval"]["headers"],
            json={"moderation_status": "approved"},
        )
        assert approved.status_code == 200, approved.text

        await db_session.refresh(club)
        assert club.summary == "new summary"
        assert club.description == "new description"

    async def test_approve_legacy_overlong_request_is_4xx_not_500(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        club = await self._make_club(db_session)
        legacy = ClubUpdateRequest(
            club_id=club.id,
            requestor_id=self.configured_users["pres_approval"]["user"].id,
            moderation_status=ModerationStatusEnum.pending,
            summary="X" * 60,
            update_fields=["summary"],
        )
        db_session.add(legacy)
        await db_session.flush()
        await db_session.refresh(legacy)

        resp = await client.patch(
            f"/moderations/clubs/update-requests/{legacy.id}",
            headers=self.configured_users["mod_approval"]["headers"],
            json={"moderation_status": "approved"},
        )
        assert resp.status_code == 400, resp.text
        assert resp.json()["error_code"] == "MODERATION_PAYLOAD_INVALID"

    async def test_pending_list_tolerates_legacy_overlong_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        club = await self._make_club(db_session)
        db_session.add(
            ClubUpdateRequest(
                club_id=club.id,
                requestor_id=self.configured_users["pres_approval"]["user"].id,
                moderation_status=ModerationStatusEnum.pending,
                summary="X" * 60,
                update_fields=["summary"],
            ),
        )
        await db_session.flush()

        resp = await client.get(
            "/moderations/clubs/update-requests",
            headers=self.configured_users["mod_approval"]["headers"],
            params={"size": 50},
        )
        assert resp.status_code == 200, resp.text
