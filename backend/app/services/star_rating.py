from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubStarLevelEnum
from app.models.club_activity import ClubActivity
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
)
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum, User, UserGradeEnum
from app.schemas.star_rating import StarRatingBreakdown, StarRatingResponse
from app.services.errors import ClubNotFoundError

_MEETING_ATTENDANCE_SCORE = 10
_SECTION_2_1_CAP = 50
_SPECIAL_BONUSES_CAP = 10
_TOTAL_SCORE_CAP = 100
_CLUB_HISTORY_MIN_YEARS = 2
_GROWTH_STORY_SCORE = 5
_CROSS_GRADE_SCORE = 5
_CLUB_HISTORY_SCORE = 5
_ALL_GRADE_LEVELS = {7, 8, 9, 10, 11, 12}
_CROSS_GRADE_MIN_MEMBERS = 25
_COMPETITION_MAX = 13

_INTERNAL_ACTIVITY_THRESHOLDS: list[tuple[int, int]] = [
    (15, 30),
    (10, 20),
    (5, 10),
    (3, 3),
]

_STAR_LEVEL_THRESHOLDS: list[tuple[int, ClubStarLevelEnum]] = [
    (90, ClubStarLevelEnum.honorary),
    (80, ClubStarLevelEnum.five_star),
    (70, ClubStarLevelEnum.four_star),
    (50, ClubStarLevelEnum.three_star),
    (30, ClubStarLevelEnum.two_star),
    (10, ClubStarLevelEnum.one_star),
]


class StarRatingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate_score(self, club_id: int) -> StarRatingResponse:
        club = await self.db.get(Club, club_id)
        if club is None:
            raise ClubNotFoundError(club_id)

        current_term = await self._get_current_term()

        # 获取本学期的星级评价申请
        application = await self._get_application(club_id, current_term)

        # 一、会议出勤 (0 或 10)
        has_federation = await self._has_federation_participation(
            club_id,
            current_term,
        )
        meeting_score = _MEETING_ATTENDANCE_SCORE if has_federation else 0

        # 二.1 活动参与 (校级 + 大型)
        raw_activity = await self._calc_activity_participation_score(
            club_id,
            current_term,
        )

        # 二.1 竞赛得分 — cap at rubric max of 13
        raw_competition = self._get_competition_score(application)
        competition_score = min(raw_competition, _COMPETITION_MAX)

        # 二.1 合计 (上限 50); competition is counted first so it's
        # never zeroed in the breakdown, then activity fills remainder.
        competition_breakdown = competition_score
        activity_participation = min(
            raw_activity,
            _SECTION_2_1_CAP - competition_breakdown,
        )
        section_2_1 = activity_participation + competition_breakdown

        # 二.2 内部活动
        internal_count = await self._count_internal_activities(
            club_id,
            current_term,
        )
        internal_score = self._internal_activity_score(internal_count)

        # 三、特色加分
        growth_story = self._get_growth_story_score(application)
        cross_grade = await self._calc_cross_grade_influence(
            club_id,
            application,
        )
        age_years = self._club_age_years(club)
        history_score = (
            _CLUB_HISTORY_SCORE if age_years >= _CLUB_HISTORY_MIN_YEARS else 0
        )
        # 三、特色加分 — components are pre-cap raw values;
        # their sum may exceed special_bonuses (capped at 10).
        special_bonuses = min(
            growth_story + cross_grade + history_score,
            _SPECIAL_BONUSES_CAP,
        )

        # 总分
        total = min(
            meeting_score + section_2_1 + internal_score + special_bonuses,
            _TOTAL_SCORE_CAP,
        )

        star_level = self._determine_star_level(total)

        return StarRatingResponse(
            club_id=club_id,
            total_score=total,
            star_level=star_level,
            breakdown=StarRatingBreakdown(
                meeting_attendance=meeting_score,
                activity_participation=activity_participation,
                competition=competition_breakdown,
                section_2_1_total=section_2_1,
                internal_activities=internal_score,
                growth_story=growth_story,
                cross_grade_influence=cross_grade,
                club_history=history_score,
                special_bonuses=special_bonuses,
            ),
            internal_activity_count=internal_count,
            has_federation_participation=has_federation,
            club_age_years=round(age_years, 2),
        )

    # ── helpers ──────────────────────────────────────────────

    async def _get_current_term(self) -> AcademicTerm | None:
        result = await self.db.execute(
            select(AcademicTerm).where(AcademicTerm.is_current.is_(True)),
        )
        return result.scalars().first()

    async def _get_application(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> StarLevelApplication | None:
        if term is None:
            return None
        result = await self.db.execute(
            select(StarLevelApplication).where(
                StarLevelApplication.club_id == club_id,
                StarLevelApplication.academic_term_id == term.id,
            ),
        )
        return result.scalars().first()

    @staticmethod
    def _get_competition_score(
        application: StarLevelApplication | None,
    ) -> int:
        """竞赛得分从已审核的 StarLevelApplication 中获取."""
        if application is None or application.audit_status != AuditStatusEnum.approved:
            return 0
        return application.final_contest_score or 0

    @staticmethod
    def _get_growth_story_score(
        application: StarLevelApplication | None,
    ) -> int:
        if (
            application is None
            or application.audit_status != AuditStatusEnum.approved
            or not application.growth_story_approved
        ):
            return 0
        return _GROWTH_STORY_SCORE

    async def _calc_cross_grade_influence(
        self,
        club_id: int,
        application: StarLevelApplication | None,
    ) -> int:
        """计算跨年级影响力得分.

        两种方式:
        1. 设置了目标级部 → 目标级部成员 ≥25 人
        2. 未设置目标级部 → 成员覆盖全部 6 个年级
        """
        # 获取活跃成员的年级分布
        grade_counts = await self._count_members_by_grade_level(club_id)

        if (
            application is not None
            and application.audit_status == AuditStatusEnum.approved
        ):
            target_grades = {
                g
                for g in (application.target_grade_1, application.target_grade_2)
                if g is not None
            }
            if target_grades:
                target_levels = {g.grade_level for g in target_grades}
                total_in_target = sum(
                    count
                    for level, count in grade_counts.items()
                    if level in target_levels
                )
                if total_in_target >= _CROSS_GRADE_MIN_MEMBERS:
                    return _CROSS_GRADE_SCORE
                return 0

        # 未设置目标级部: 检查是否覆盖全部 6 个年级
        if set(grade_counts.keys()) >= _ALL_GRADE_LEVELS:
            return _CROSS_GRADE_SCORE

        return 0

    async def _count_members_by_grade_level(
        self,
        club_id: int,
    ) -> dict[int, int]:
        """统计社团活跃成员的年级分布 (按 grade_level 分组).

        Returns: {grade_level: count}, e.g. {7: 10, 8: 15, ...}
        """
        stmt = (
            select(User.grade, func.count())
            .join(ClubMember, ClubMember.user_id == User.id)
            .where(
                ClubMember.club_id == club_id,
                ClubMember.membership.in_(
                    [
                        ClubMembershipEnum.member,
                        ClubMembershipEnum.president,
                        ClubMembershipEnum.vice_president,
                    ],
                ),
                User.grade.isnot(None),
            )
            .group_by(User.grade)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        counts: dict[int, int] = {}
        for grade_enum_value, count in rows:
            if isinstance(grade_enum_value, UserGradeEnum):
                level = grade_enum_value.grade_level
            else:
                level = UserGradeEnum(grade_enum_value).grade_level
            counts[level] = counts.get(level, 0) + count
        return counts

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
                GeneralActivity.level == GeneralActivityLevelEnum.club_federation,
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
        return total

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
        for threshold, score in _INTERNAL_ACTIVITY_THRESHOLDS:
            if count >= threshold:
                return score
        return 0

    @staticmethod
    def _determine_star_level(total: int) -> ClubStarLevelEnum:
        """根据总分判定星级."""
        for threshold, level in _STAR_LEVEL_THRESHOLDS:
            if total >= threshold:
                return level
        return ClubStarLevelEnum.none

    @staticmethod
    def _club_age_years(club: Club) -> float:
        now = datetime.now(tz=UTC)
        created = club.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        delta = now - created
        return delta.days / 365.25
