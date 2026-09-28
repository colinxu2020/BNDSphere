from datetime import date
from typing import ClassVar

from httpx import AsyncClient

from app.models.user import RoleEnum


class TestAcademicTermConflicts:
    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {"username": "term-conflicts-admin", "role": RoleEnum.admin},
    ]
    configured_users: ClassVar[dict[str, dict[str, object]]]

    async def test_duplicate_term_name_returns_conflict_without_clearing_current(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["term-conflicts-admin"]["headers"]
        assert isinstance(headers, dict)
        first = await client.post(
            "/admin/academic-terms/",
            headers=headers,
            json={
                "term_name": "2026 test term",
                "start_date": str(date(2026, 9, 1)),
                "end_date": str(date(2027, 1, 1)),
                "is_current": True,
            },
        )
        assert first.status_code == 201
        duplicate = await client.post(
            "/admin/academic-terms/",
            headers=headers,
            json={
                "term_name": "2026 test term",
                "start_date": str(date(2027, 9, 1)),
                "end_date": str(date(2028, 1, 1)),
                "is_current": True,
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error_code"] == "DATABASE_CONFLICT"
        read = await client.get(
            f"/admin/academic-terms/{first.json()['id']}",
            headers=headers,
        )
        assert read.status_code == 200
        assert read.json()["is_current"] is True

    async def test_renaming_term_to_an_existing_name_returns_conflict(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["term-conflicts-admin"]["headers"]
        assert isinstance(headers, dict)
        existing = await client.post(
            "/admin/academic-terms/",
            headers=headers,
            json={
                "term_name": "2027 patch target",
                "start_date": str(date(2027, 9, 1)),
                "end_date": str(date(2028, 1, 1)),
                "is_current": False,
            },
        )
        assert existing.status_code == 201
        second = await client.post(
            "/admin/academic-terms/",
            headers=headers,
            json={
                "term_name": "2028 patch source",
                "start_date": str(date(2028, 9, 1)),
                "end_date": str(date(2029, 1, 1)),
                "is_current": False,
            },
        )
        assert second.status_code == 201
        duplicate = await client.patch(
            f"/admin/academic-terms/{second.json()['id']}",
            headers=headers,
            json={"term_name": "2027 patch target"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error_code"] == "DATABASE_CONFLICT"
