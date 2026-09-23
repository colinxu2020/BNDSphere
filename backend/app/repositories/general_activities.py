from datetime import datetime
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Club, GeneralActivity, User
from app.models.club import ClubStatusEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivityLevelEnum,
)
from app.models.user import AuditStatusEnum
from app.repositories.base import RepositoryBase
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityUpdate,
    FederationRecordUpdate,
    GeneralActivityCreate,
    GeneralActivityUpdate,
)
from app.utils.like import escape_like

# 公开回显只加载「已审核通过 + 社团状态正常」的活动参与记录:
# pending/rejected 记录的 proof_files 等内容未经社联审核, 匿名访客不应看到.
_PUBLIC_RECORDS_OPTION = selectinload(
    GeneralActivity.club_records.and_(
        ClubGeneralActivityRecord.audit_status == AuditStatusEnum.approved,
        ClubGeneralActivityRecord.club.has(Club.status == ClubStatusEnum.normal),
    ),
)


class GeneralActivityRepository(
    RepositoryBase[GeneralActivity, GeneralActivityCreate, GeneralActivityUpdate],
):
    model = GeneralActivity

    async def get_public(self, id_: int) -> GeneralActivity | None:
        stmt = (
            select(self.model)
            .where(self.model.id == id_)
            .options(_PUBLIC_RECORDS_OPTION)
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def get_multi(
        self,
        search: str | None = None,
        level: GeneralActivityLevelEnum | None = None,
        *,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        has_poster: bool | None = None,
        public_only: bool = False,
    ) -> Page[GeneralActivity]:
        stmt = select(self.model).order_by(
            GeneralActivity.starts_at.desc().nullslast(),
            GeneralActivity.created_at.desc(),
        )
        if public_only:
            stmt = stmt.options(_PUBLIC_RECORDS_OPTION)
        if level is not None:
            stmt = stmt.where(self.model.level == level)
        if search is not None:
            pattern = f"%{escape_like(search)}%"
            stmt = stmt.where(self.model.name.ilike(pattern, escape="\\"))
        if starts_before is not None:
            stmt = stmt.where(self.model.starts_at <= starts_before)
        if ends_after is not None:
            stmt = stmt.where(self.model.ends_at >= ends_after)
        if has_poster is not None:
            if has_poster:
                stmt = stmt.where(self.model.poster_uri.is_not(None))
            else:
                stmt = stmt.where(self.model.poster_uri.is_(None))
        return cast("Page[GeneralActivity]", await apaginate(self.db, stmt))


class ClubGeneralActivityRepository(
    RepositoryBase[
        ClubGeneralActivityRecord,
        ClubGeneralActivityCreate,
        ClubGeneralActivityUpdate,
    ],
):
    model = ClubGeneralActivityRecord

    async def get_by_club(self, club: Club) -> Page[ClubGeneralActivityRecord]:
        stmt = select(self.model).where(self.model.club == club)
        return cast("Page[ClubGeneralActivityRecord]", await apaginate(self.db, stmt))

    async def find_by_club_and_activity(
        self,
        club: Club,
        activity: GeneralActivity,
    ) -> ClubGeneralActivityRecord | None:
        stmt = select(self.model).where(
            self.model.club == club,
            self.model.activity_id == activity.id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_by_club_id_and_activity_id(
        self,
        club_id: int,
        activity_id: int,
    ) -> ClubGeneralActivityRecord | None:
        stmt = select(self.model).where(
            self.model.club_id == club_id,
            self.model.activity_id == activity_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def review_record(
        self,
        db_obj: ClubGeneralActivityRecord,
        obj_in: FederationRecordUpdate,
        auditor: User,
    ) -> ClubGeneralActivityRecord:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db_obj.auditor = auditor
        db_obj.auditor_id = auditor.id

        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
