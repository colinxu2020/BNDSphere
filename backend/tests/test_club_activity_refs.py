from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicTerm, ClubActivity
from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum


class TestClubActivityRefs:
    @pytest_asyncio.fixture(scope="class")
    async def clubs(self, db_session: AsyncSession) -> dict[str, int]:
        now = datetime.now(UTC)
        term = AcademicTerm(
            term_name="activity-refs-term",
            start_date=now.date(),
            end_date=(now + timedelta(days=180)).date(),
        )
        db_session.add(term)
        await db_session.flush()
        ids = {}
        for status in ClubStatusEnum:
            club = Club(
                name=f"Refs {status}",
                summary="summary",
                description="description",
                category=ClubCategoryEnum.natural_science,
                status=status,
            )
            db_session.add(club)
            await db_session.flush()
            ids[status.value] = club.id
            for index in range(55 if status == ClubStatusEnum.normal else 2):
                db_session.add(
                    ClubActivity(
                        club_id=club.id,
                        academic_term_id=term.id,
                        name=f"{status} activity {index}",
                        description="not part of a ref",
                        location="location",
                        start_time=now + timedelta(days=index),
                        end_time=now + timedelta(days=index, hours=1),
                    ),
                )
        await db_session.commit()
        return ids

    @pytest.mark.parametrize("status", list(ClubStatusEnum))
    async def test_anonymous_refs_match_existing_list_visibility_and_order(
        self, client: AsyncClient, clubs: dict[str, int], status: ClubStatusEnum
    ) -> None:
        path = f"/clubs/{clubs[status.value]}/activities/"
        existing = await client.get(path, params={"size": 100})
        refs = await client.get(f"{path}refs/")
        assert existing.status_code == refs.status_code == 200
        assert refs.json() == [
            {"id": item["id"], "name": item["name"]}
            for item in existing.json()["items"]
        ]
        assert len(refs.json()) == (55 if status == ClubStatusEnum.normal else 2)

    async def test_missing_club_matches_existing_list(
        self, client: AsyncClient
    ) -> None:
        path = "/clubs/2147483647/activities/"
        existing = await client.get(path)
        refs = await client.get(f"{path}refs/")
        assert refs.status_code == existing.status_code == 404
        assert refs.json() == existing.json()
