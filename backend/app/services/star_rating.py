from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_term import AcademicTerm
from app.models.club import Club
from app.models.club_activity import ClubActivity
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
)
from app.models.user import AuditStatusEnum
from app.schemas.star_rating import StarRatingBreakdown, StarRatingResponse
from app.services.errors import ClubNotFoundError

_MEETING_ATTENDANCE_SCORE = 10
_ACTIVITY_PARTICIPATION_CAP = 45
_INTERNAL_ACTIVITY_CAP = 25
_CLUB_HISTORY_SCORE = 5
_TOTAL_SCORE_CAP = 100
_CLUB_HISTORY_MIN_YEARS = 2


class StarRatingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate_score(self, club_id: int) -> StarRatingResponse:
        club = await self.db.get(Club, club_id)
        if club is None:
            raise ClubNotFoundError(club_id)

        current_term = await self._get_current_term()

        # 一、会议出勤
        has_federation = await self._has_federation_participation(
            club_id,
            current_term,
        )
        meeting_score = _MEETING_ATTENDANCE_SCORE if has_federation else 0

        # 二.1 活动参与
        activity_score = await self._calc_activity_participation_score(
            club_id,
            current_term,
        )

        # 二.2 内部活动
        internal_count = await self._count_internal_activities(
            club_id,
            current_term,
        )
        internal_score = self._internal_activity_score(internal_count)

        # 三、社团历史
        age_years = self._club_age_years(club)
        history_score = (
            _CLUB_HISTORY_SCORE if age_years > _CLUB_HISTORY_MIN_YEARS else 0
        )

        total = min(
            meeting_score + activity_score + internal_score + history_score,
            _TOTAL_SCORE_CAP,
        )

        return StarRatingResponse(
            club_id=club_id,
            total_score=total,
            breakdown=StarRatingBreakdown(
                meeting_attendance=meeting_score,
                activity_participation=activity_score,
                internal_activities=internal_score,
                club_history=history_score,
            ),
            internal_activity_count=internal_count,
            has_federation_participation=has_federation,
            club_age_years=round(age_years, 2),
        )

    async def _get_current_term(self) -> AcademicTerm | None:
        result = await self.db.execute(
            select(AcademicTerm).where(AcademicTerm.is_current.is_(True)),
        )
        return result.scalars().first()

    async def _has_federation_participation(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> bool:
        """Check if the club participated in any club_federation activity."""
        stmt = (
            select(ClubGeneralActivityRecord.id)
            .join(
                GeneralActivity,
                ClubGeneralActivityRecord.activity_id == GeneralActivity.id,
            )
            .where(
                ClubGeneralActivityRecord.club_id == club_id,
                GeneralActivity.level == GeneralActivityLevelEnum.federation,
            )
            .limit(1)
        )
        if term is not None:
            stmt = stmt.where(GeneralActivity.academic_term_id == term.id)
        result = await self.db.execute(stmt)
        return result.first() is not None

    async def _calc_activity_participation_score(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> int:
        """Sum final_score of approved school/large activity records."""
        stmt = (
            select(func.coalesce(func.sum(ClubGeneralActivityRecord.final_score), 0))
            .join(
                GeneralActivity,
                ClubGeneralActivityRecord.activity_id == GeneralActivity.id,
            )
            .where(
                ClubGeneralActivityRecord.club_id == club_id,
                ClubGeneralActivityRecord.audit_status == AuditStatusEnum.approved,
                GeneralActivity.level.in_(
                    [
                        GeneralActivityLevelEnum.school,
                        GeneralActivityLevelEnum.large,
                    ],
                ),
            )
        )
        if term is not None:
            stmt = stmt.where(GeneralActivity.academic_term_id == term.id)
        result = await self.db.execute(stmt)
        total: int = result.scalar_one()
        return min(total, _ACTIVITY_PARTICIPATION_CAP)

    async def _count_internal_activities(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> int:
        """Count the club's own activities in the current term."""
        stmt = (
            select(func.count())
            .select_from(ClubActivity)
            .where(
                ClubActivity.club_id == club_id,
            )
        )
        if term is not None:
            stmt = stmt.where(ClubActivity.academic_term_id == term.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _internal_activity_score(count: int) -> int:
        if count >= 15:  # noqa: PLR2004
            return 25
        if count >= 10:  # noqa: PLR2004
            return 20
        if count >= 5:  # noqa: PLR2004
            return 10
        if count >= 3:  # noqa: PLR2004
            return 3
        return 0

    @staticmethod
    def _club_age_years(club: Club) -> float:
        now = datetime.now(tz=UTC)
        created = club.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        delta = now - created
        return delta.days / 365.25
