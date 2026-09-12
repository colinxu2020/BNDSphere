from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_term import AcademicTerm
from app.models.club import Club
from app.models.club_activity import ClubActivity
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
)
from app.models.joint_activity import JointActivity, JointActivityParticipation
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum, User, UserGradeEnum
from app.models.verifications.verification_common import VerificationStatusEnum

_MAX_SCORED_JOINT_ACTIVITIES = 2


class StarRatingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_club(self, club_id: int) -> Club | None:
        return await self.db.get(Club, club_id)

    async def get_current_term(self) -> AcademicTerm | None:
        result = await self.db.execute(
            select(AcademicTerm).where(AcademicTerm.is_current.is_(True)),
        )
        return result.scalars().first()

    async def get_term(self, term_id: int) -> AcademicTerm | None:
        return await self.db.get(AcademicTerm, term_id)

    async def get_application(
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

    async def count_members_by_grade_level(
        self,
        club_id: int,
    ) -> dict[int, int]:
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
        rows = (await self.db.execute(stmt)).all()

        counts: dict[int, int] = {}
        for grade_enum_value, count in rows:
            if isinstance(grade_enum_value, UserGradeEnum):
                level = grade_enum_value.grade_level
            else:
                level = UserGradeEnum(grade_enum_value).grade_level
            counts[level] = counts.get(level, 0) + count
        return counts

    async def has_federation_participation(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> bool:
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

    async def sum_approved_activity_scores(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> int:
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
        general_total: int = result.scalar_one()

        joint_scores_stmt = (
            select(JointActivity.final_score.label("score"))
            .join(
                JointActivityParticipation,
                JointActivityParticipation.activity_id == JointActivity.id,
            )
            .where(
                JointActivityParticipation.club_id == club_id,
                JointActivity.final_status == VerificationStatusEnum.approved,
            )
            .order_by(JointActivity.final_score.desc(), JointActivity.id)
            .limit(_MAX_SCORED_JOINT_ACTIVITIES)
        )
        if term is not None:
            joint_scores_stmt = joint_scores_stmt.where(
                JointActivity.academic_term_id == term.id,
            )
        joint_scores = joint_scores_stmt.subquery()
        joint_stmt = select(func.coalesce(func.sum(joint_scores.c.score), 0))
        joint_result = await self.db.execute(joint_stmt)
        joint_total: int = joint_result.scalar_one()
        return general_total + joint_total

    async def count_internal_activities(
        self,
        club_id: int,
        term: AcademicTerm | None,
    ) -> int:
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
