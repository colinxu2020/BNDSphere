from datetime import datetime
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select

from app.models import JointActivity, JointActivityParticipation
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import User
from app.models.verifications.verification_common import VerificationStatusEnum
from app.repositories.base import RepositoryBase
from app.schemas.joint_activities import (
    JointActivityCreate,
    JointActivityUpdate,
)
from app.schemas.verifications.joint_activity import JointActivityFinalVerification


class JointActivityRepository(
    RepositoryBase[JointActivity, JointActivityCreate, JointActivityUpdate],
):
    model = JointActivity

    async def get_multi(
        self,
        *,
        public_only: bool,
        search: str | None = None,
        club_id: int | None = None,
    ) -> Page[JointActivity]:
        stmt = select(self.model).order_by(
            self.model.starts_at.desc(),
            self.model.created_at.desc(),
        )
        if public_only:
            stmt = stmt.where(
                self.model.preliminary_status == ModerationStatusEnum.approved,
            )
        if search:
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
        if club_id is not None:
            stmt = stmt.join(
                JointActivityParticipation,
                JointActivityParticipation.activity_id == self.model.id,
            ).where(JointActivityParticipation.club_id == club_id)
        return cast("Page[JointActivity]", await apaginate(self.db, stmt))

    async def create_with_initiator(
        self,
        obj_in: JointActivityCreate,
        *,
        club_id: int,
        user_id: int,
    ) -> JointActivity:
        activity = JointActivity(
            **obj_in.model_dump(),
            initiator_club_id=club_id,
            created_by_user_id=user_id,
        )
        self.db.add(activity)
        await self.db.flush()
        self.db.add(
            JointActivityParticipation(
                activity_id=activity.id,
                club_id=club_id,
                registered_by_user_id=user_id,
                is_initiator=True,
            ),
        )
        await self.db.flush()
        await self.db.refresh(activity)
        return activity

    async def get_participation(
        self,
        activity_id: int,
        club_id: int,
    ) -> JointActivityParticipation | None:
        stmt = select(JointActivityParticipation).where(
            JointActivityParticipation.activity_id == activity_id,
            JointActivityParticipation.club_id == club_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add_participation(
        self,
        *,
        activity_id: int,
        club_id: int,
        user_id: int,
    ) -> JointActivityParticipation:
        participation = JointActivityParticipation(
            activity_id=activity_id,
            club_id=club_id,
            registered_by_user_id=user_id,
            is_initiator=False,
        )
        self.db.add(participation)
        await self.db.flush()
        await self.db.refresh(participation)
        return participation

    async def preliminary_review(
        self,
        activity: JointActivity,
        *,
        status: ModerationStatusEnum,
        moderator: User,
        reviewed_at: datetime,
    ) -> JointActivity:
        activity.preliminary_status = status
        activity.preliminary_auditor_id = moderator.id
        activity.preliminary_reviewed_at = reviewed_at
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        return activity

    async def final_review(
        self,
        activity: JointActivity,
        verification: JointActivityFinalVerification,
        *,
        verifier: User,
        reviewed_at: datetime,
    ) -> JointActivity:
        activity.final_status = verification.verification_status
        activity.final_score = (
            verification.final_score
            if verification.verification_status == VerificationStatusEnum.approved
            else 0
        )
        activity.final_auditor_id = verifier.id
        activity.final_reviewed_at = reviewed_at
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        return activity
