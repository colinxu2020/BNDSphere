from datetime import UTC, datetime

from app.models.club import Club, ClubStarLevelEnum
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum
from app.repositories.star_rating import StarRatingRepository
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
    def __init__(self, repository: StarRatingRepository) -> None:
        self.repository = repository

    async def calculate_score(self, club_id: int) -> StarRatingResponse:
        club = await self.repository.get_club(club_id)
        if club is None:
            raise ClubNotFoundError(club_id)

        current_term = await self.repository.get_current_term()
        application = await self.repository.get_application(club_id, current_term)

        has_federation = await self.repository.has_federation_participation(
            club_id,
            current_term,
        )
        meeting_score = _MEETING_ATTENDANCE_SCORE if has_federation else 0

        raw_activity = await self.repository.sum_approved_activity_scores(
            club_id,
            current_term,
        )

        raw_competition = self._get_competition_score(application)
        competition_score = min(raw_competition, _COMPETITION_MAX)

        competition_breakdown = competition_score
        activity_participation = min(
            raw_activity,
            _SECTION_2_1_CAP - competition_breakdown,
        )
        section_2_1 = activity_participation + competition_breakdown

        internal_count = await self.repository.count_internal_activities(
            club_id,
            current_term,
        )
        internal_score = self._internal_activity_score(internal_count)

        growth_story = self._get_growth_story_score(application)
        cross_grade = await self._calc_cross_grade_influence(
            club_id,
            application,
        )
        age_years = self._club_age_years(club)
        history_score = (
            _CLUB_HISTORY_SCORE if age_years >= _CLUB_HISTORY_MIN_YEARS else 0
        )
        special_bonuses = min(
            growth_story + cross_grade + history_score,
            _SPECIAL_BONUSES_CAP,
        )

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
        1. 设置了目标级部 -> 目标级部成员 >=25 人
        2. 未设置目标级部 -> 成员覆盖全部 6 个年级
        """
        grade_counts = await self.repository.count_members_by_grade_level(club_id)

        if (
            application is not None
            and application.audit_status == AuditStatusEnum.approved
        ):
            target_grades = {
                grade
                for grade in (
                    application.target_grade_1,
                    application.target_grade_2,
                )
                if grade is not None
            }
            if target_grades:
                target_levels = {grade.grade_level for grade in target_grades}
                total_in_target = sum(
                    count
                    for level, count in grade_counts.items()
                    if level in target_levels
                )
                if total_in_target >= _CROSS_GRADE_MIN_MEMBERS:
                    return _CROSS_GRADE_SCORE
                return 0

        if set(grade_counts.keys()) >= _ALL_GRADE_LEVELS:
            return _CROSS_GRADE_SCORE

        return 0

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
