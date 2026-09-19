import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum


class TestClubSearch:
    @pytest_asyncio.fixture(scope="class", autouse=True)
    async def seed_club(self, db_session: AsyncSession) -> None:
        db_session.add(
            Club(
                name="Exact Search Club",
                summary="A club created for the search regression test.",
                description="Search results must serialize club models.",
                category=ClubCategoryEnum.information_technology,
                status=ClubStatusEnum.normal,
            ),
        )
        await db_session.commit()

    async def test_search_hit_returns_club_item(self, client: AsyncClient) -> None:
        response = await client.get(
            "/clubs/",
            params={"search": "Exact Search Club"},
        )

        assert response.status_code == 200
        assert [item["name"] for item in response.json()["items"]] == [
            "Exact Search Club",
        ]
