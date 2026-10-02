import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum


def _club(name: str, status: ClubStatusEnum) -> Club:
    return Club(
        name=name,
        summary=f"{name} summary",
        description=f"{name} description",
        category=ClubCategoryEnum.information_technology,
        status=status,
    )


class TestClubRefs:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def seed_clubs(self, db_session: AsyncSession) -> None:
        db_session.add_all(
            [
                _club("Ref Normal Club", ClubStatusEnum.normal),
                _club("Ref Unreviewed Club", ClubStatusEnum.unreviewed),
                _club("Ref Archived Club", ClubStatusEnum.archived),
            ],
        )
        await db_session.commit()

    async def test_refs_only_include_normal_clubs(self, client: AsyncClient) -> None:
        response = await client.get("/clubs/refs/", params={"size": 100})

        assert response.status_code == 200
        names = {item["name"] for item in response.json()["items"]}
        assert "Ref Normal Club" in names
        assert "Ref Unreviewed Club" not in names
        assert "Ref Archived Club" not in names

    async def test_refs_only_contain_id_and_name(self, client: AsyncClient) -> None:
        response = await client.get("/clubs/refs/", params={"size": 100})

        assert response.status_code == 200
        items = response.json()["items"]
        assert items
        assert all(set(item) == {"id", "name"} for item in items)

    async def test_refs_search(self, client: AsyncClient) -> None:
        response = await client.get(
            "/clubs/refs/",
            params={"search": "Ref Normal Club"},
        )

        assert response.status_code == 200
        assert [item["name"] for item in response.json()["items"]] == [
            "Ref Normal Club",
        ]
