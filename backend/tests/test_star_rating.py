from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubCategoryEnum
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum
from app.repositories.star_rating import StarRatingRepository
from app.services.star_rating import StarRatingService


class StubStarRatingRepository:
    def __init__(
        self,
        *,
        activity_score: int = 0,
        internal_count: int = 0,
        attends_meeting: bool = False,
        application: StarLevelApplication | None = None,
        grade_counts: dict[int, int] | None = None,
    ) -> None:
        self.club = Club(
            id=1,
            name="Test Club",
            summary="Test",
            description="Test",
            category=ClubCategoryEnum.other,
            created_at=datetime.now(tz=UTC) - timedelta(days=3 * 366),
        )
        self.activity_score = activity_score
        self.internal_count = internal_count
        self.attends_meeting = attends_meeting
        self.application = application
        self.grade_counts = grade_counts or {}

    async def get_club(self, club_id: int) -> Club | None:
        return self.club if club_id == self.club.id else None

    async def get_current_term(self) -> AcademicTerm | None:
        return None

    async def get_application(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> StarLevelApplication | None:
        return self.application

    async def has_federation_participation(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> bool:
        return self.attends_meeting

    async def sum_approved_activity_scores(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> int:
        return self.activity_score

    async def count_internal_activities(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> int:
        return self.internal_count

    async def count_members_by_grade_level(self, club_id: int) -> dict[int, int]:
        return self.grade_counts


def make_service(repository: StubStarRatingRepository) -> StarRatingService:
    return StarRatingService(cast("StarRatingRepository", repository))


@pytest.mark.parametrize(
    ("activity_count", "expected_score"),
    [(0, 0), (2, 0), (3, 3), (5, 10), (10, 20), (15, 25), (20, 25)],
)
async def test_internal_activity_thresholds(
    activity_count: int,
    expected_score: int,
) -> None:
    repository = StubStarRatingRepository(internal_count=activity_count)

    rating = await make_service(repository).calculate_score(repository.club.id)

    assert rating.breakdown.internal_activities == expected_score


async def test_latest_section_caps_allow_a_100_point_rating() -> None:
    application = StarLevelApplication(
        club_id=1,
        academic_term_id=1,
        audit_status=AuditStatusEnum.approved,
        final_contest_score=20,
        growth_story_approved=True,
        target_grade_1=None,
        target_grade_2=None,
    )
    repository = StubStarRatingRepository(
        activity_score=40,
        internal_count=15,
        attends_meeting=True,
        application=application,
        grade_counts={7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1},
    )

    rating = await make_service(repository).calculate_score(repository.club.id)

    assert rating.total_score == 100
    assert rating.breakdown.section_2_1_total == 55
    assert rating.breakdown.competition == 20
    assert rating.breakdown.activity_participation == 35
    assert rating.breakdown.internal_activities == 25
    assert rating.breakdown.special_bonuses == 10


class ScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class CapturingSession:
    def __init__(self) -> None:
        self.statements: list[object] = []

    async def execute(self, statement: object) -> ScalarResult:
        self.statements.append(statement)
        return ScalarResult(8 if len(self.statements) == 1 else 16)


async def test_joint_activity_score_is_limited_to_two_activities() -> None:
    session = CapturingSession()
    repository = StarRatingRepository(cast("AsyncSession", session))

    total = await repository.sum_approved_activity_scores(1, None)

    joint_score_query = str(
        session.statements[1].compile(compile_kwargs={"literal_binds": True}),
    )
    assert total == 24
    assert "LIMIT 2" in joint_score_query
