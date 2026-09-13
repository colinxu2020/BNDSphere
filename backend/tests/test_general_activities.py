"""Regression tests for the general-activity stored-XSS audit finding.

Covers the two unfixed root causes from the 2026-09 security report:
1. ``proof_files`` accepted arbitrary strings (javascript:/data:/phishing URLs)
   on the write path — now must be OSS-hosted application_file URLs.
2. The public activity endpoints echoed every club record, including pending
   (unreviewed) ones and records of non-normal clubs — now only approved
   records from normal clubs are returned publicly, while federation staff
   keep a full view through their own endpoint.
"""

from datetime import date
from typing import ClassVar, TypedDict

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import oss_settings
from app.models import User
from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
    ParticipationTypeEnum,
)
from app.models.user import AuditStatusEnum, RoleEnum


class ConfiguredUser(TypedDict):
    """Shape of the ``configured_users`` mapping set by ``setup_class_users``."""

    headers: dict[str, str]
    user: User


def _oss_file_url(filename: str) -> str:
    base = oss_settings().oss_public_base_url.rstrip("/")
    return f"{base}/application_files/{filename}"


class TestProofFilesValidation:
    """Write path: proof_files must be OSS-hosted URLs, never raw strings."""

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {"username": "ga_president", "password": "president-pw-0001"},
    ]

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def seed_data(
        self,
        request: pytest.FixtureRequest,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        president: User = request.cls.configured_users["ga_president"]["user"]

        term = AcademicTerm(
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 31),
            is_current=True,
        )
        club = Club(
            name="proof validation club",
            summary="s",
            description="d",
            category=ClubCategoryEnum.other,
            status=ClubStatusEnum.normal,
        )
        db_session.add_all([term, club])
        await db_session.flush()

        create_activity = GeneralActivity(
            name="proof create activity",
            description="d",
            level=GeneralActivityLevelEnum.large,
        )
        update_activity = GeneralActivity(
            name="proof update activity",
            description="d",
            level=GeneralActivityLevelEnum.large,
        )
        db_session.add_all([create_activity, update_activity])
        await db_session.flush()

        db_session.add(
            ClubMember(
                user_id=president.id,
                club_id=club.id,
                membership=ClubMembershipEnum.president,
            ),
        )
        # Pending record the PATCH tests target (update requires pending).
        db_session.add(
            ClubGeneralActivityRecord(
                club_id=club.id,
                activity_id=update_activity.id,
                participation_type=ParticipationTypeEnum.participate_only,
                requested_score=1,
                proof_files=[],
            ),
        )
        await db_session.flush()

        request.cls.club_id = club.id
        request.cls.create_activity_id = create_activity.id
        request.cls.update_activity_id = update_activity.id
        # Release the session savepoint so seeded rows survive request-time
        # rollbacks (same pattern as ``setup_class_users``).
        await db_session.commit()

    async def test_create_rejects_javascript_scheme(
        self,
        client: AsyncClient,
    ) -> None:
        headers = self.configured_users["ga_president"]["headers"]
        resp = await client.post(
            f"/clubs/{self.club_id}/general-activities/",
            headers=headers,
            json={
                "activity_id": self.create_activity_id,
                "participation_type": "participate_only",
                "proof_files": ["javascript:alert(document.domain)"],
                "requested_score": 1,
            },
        )
        assert resp.status_code == 422

    async def test_create_rejects_data_scheme(self, client: AsyncClient) -> None:
        headers = self.configured_users["ga_president"]["headers"]
        resp = await client.post(
            f"/clubs/{self.club_id}/general-activities/",
            headers=headers,
            json={
                "activity_id": self.create_activity_id,
                "participation_type": "participate_only",
                "proof_files": ["data:text/html,<script>alert(1)</script>"],
                "requested_score": 1,
            },
        )
        assert resp.status_code == 422

    async def test_create_rejects_external_https_url(
        self,
        client: AsyncClient,
    ) -> None:
        headers = self.configured_users["ga_president"]["headers"]
        resp = await client.post(
            f"/clubs/{self.club_id}/general-activities/",
            headers=headers,
            json={
                "activity_id": self.create_activity_id,
                "participation_type": "participate_only",
                "proof_files": ["https://phishing.example.com/proof.pdf"],
                "requested_score": 1,
            },
        )
        assert resp.status_code == 422

    async def test_create_accepts_oss_url(self, client: AsyncClient) -> None:
        headers = self.configured_users["ga_president"]["headers"]
        url = _oss_file_url("proof.pdf")
        resp = await client.post(
            f"/clubs/{self.club_id}/general-activities/",
            headers=headers,
            json={
                "activity_id": self.create_activity_id,
                "participation_type": "participate_only",
                "proof_files": [url],
                "requested_score": 1,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["proof_files"] == [url]

    async def test_update_rejects_javascript_scheme(
        self,
        client: AsyncClient,
    ) -> None:
        headers = self.configured_users["ga_president"]["headers"]
        resp = await client.patch(
            f"/clubs/{self.club_id}/general-activities/",
            headers=headers,
            json={
                "activity_id": self.update_activity_id,
                "participation_type": "participate_only",
                "proof_files": ["javascript:alert(document.domain)"],
                "requested_score": 2,
            },
        )
        assert resp.status_code == 422

    async def test_update_accepts_oss_url(self, client: AsyncClient) -> None:
        headers = self.configured_users["ga_president"]["headers"]
        url = _oss_file_url("proof-updated.pdf")
        resp = await client.patch(
            f"/clubs/{self.club_id}/general-activities/",
            headers=headers,
            json={
                "activity_id": self.update_activity_id,
                "participation_type": "participate_only",
                "proof_files": [url],
                "requested_score": 2,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["proof_files"] == [url]


class TestPublicClubRecordsEcho:
    """Read path: public endpoints must not echo unreviewed records."""

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "ga_federation",
            "password": "federation-pw-001",
            "role": RoleEnum.federation_staff,
        },
    ]

    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def seed_data(
        self,
        request: pytest.FixtureRequest,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        term = AcademicTerm(
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 31),
            is_current=True,
        )
        normal_club = Club(
            name="echo normal club",
            summary="s",
            description="d",
            category=ClubCategoryEnum.other,
            status=ClubStatusEnum.normal,
        )
        # (club_id, activity_id) 有唯一约束, pending 脏数据记录挂到另一个正常社团.
        normal_club_2 = Club(
            name="echo normal club 2",
            summary="s",
            description="d",
            category=ClubCategoryEnum.other,
            status=ClubStatusEnum.normal,
        )
        unreviewed_club = Club(
            name="echo unreviewed club",
            summary="s",
            description="d",
            category=ClubCategoryEnum.other,
            status=ClubStatusEnum.unreviewed,
        )
        db_session.add_all([term, normal_club, normal_club_2, unreviewed_club])
        await db_session.flush()

        activity = GeneralActivity(
            name="echo activity",
            description="d",
            level=GeneralActivityLevelEnum.large,
        )
        db_session.add(activity)
        await db_session.flush()

        approved = ClubGeneralActivityRecord(
            club_id=normal_club.id,
            activity_id=activity.id,
            participation_type=ParticipationTypeEnum.participate_only,
            requested_score=1,
            proof_files=[_oss_file_url("approved.pdf")],
            audit_status=AuditStatusEnum.approved,
        )
        # Simulates a legacy dirty row persisted before the write-path
        # validation existed (ORM insert bypasses the API schema).
        pending_dirty = ClubGeneralActivityRecord(
            club_id=normal_club_2.id,
            activity_id=activity.id,
            participation_type=ParticipationTypeEnum.organize,
            requested_score=1,
            proof_files=["javascript:alert(document.domain)"],
            audit_status=AuditStatusEnum.pending,
        )
        unreviewed_club_record = ClubGeneralActivityRecord(
            club_id=unreviewed_club.id,
            activity_id=activity.id,
            participation_type=ParticipationTypeEnum.participate_only,
            requested_score=1,
            proof_files=[],
            audit_status=AuditStatusEnum.approved,
        )
        db_session.add_all([approved, pending_dirty, unreviewed_club_record])
        await db_session.flush()

        request.cls.activity_id = activity.id
        request.cls.approved_record_id = approved.id
        request.cls.pending_record_id = pending_dirty.id
        request.cls.unreviewed_club_record_id = unreviewed_club_record.id
        await db_session.commit()

    async def test_public_detail_hides_unreviewed_records(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get(f"/general-activities/{self.activity_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert [r["id"] for r in body["club_records"]] == [self.approved_record_id]
        assert "javascript:" not in resp.text

    async def test_public_list_hides_unreviewed_records(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/general-activities/")
        assert resp.status_code == 200
        items = resp.json()["items"]
        item = next(i for i in items if i["id"] == self.activity_id)
        assert [r["id"] for r in item["club_records"]] == [self.approved_record_id]
        assert "javascript:" not in resp.text

    async def test_federation_list_sees_all_records(
        self,
        client: AsyncClient,
    ) -> None:
        headers = self.configured_users["ga_federation"]["headers"]
        resp = await client.get("/club-federation/general-activity/", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        item = next(i for i in items if i["id"] == self.activity_id)
        assert {r["id"] for r in item["club_records"]} == {
            self.approved_record_id,
            self.pending_record_id,
            self.unreviewed_club_record_id,
        }

    async def test_federation_list_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/club-federation/general-activity/")
        assert resp.status_code == 401
