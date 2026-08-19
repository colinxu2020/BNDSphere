from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.models import Club
from app.models.club_activity import ClubActivity
from app.models.moderations.club_activity import (
    ClubActivityCreateRequest,
    ClubActivityUpdateRequest,
)
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.repositories.base import RepositoryBase
from app.schemas.club_activity import ClubActivityCreate, ClubActivityUpdate
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreate,
    ClubActivityUpdateRequestCreate,
)
from app.schemas.moderations.moderation_common import RequestModerate


class ClubActivityRepository(
    RepositoryBase[ClubActivity, ClubActivityCreate, ClubActivityUpdate],
):
    model = ClubActivity

    async def get_club_activities(
        self,
        club: Club,
    ) -> Page[ClubActivity]:
        stmt = (
            select(ClubActivity)
            .where(ClubActivity.club_id == club.id)
            .order_by(ClubActivity.start_time.desc(), ClubActivity.id.desc())
            .options(selectinload(ClubActivity.participants))
        )
        return cast("Page[ClubActivity]", await apaginate(self.db, stmt))

    async def create_club_activity(
        self,
        club_id: int,
        obj_in: ClubActivityCreate,
    ) -> ClubActivity:
        db_activity = ClubActivity(**obj_in.model_dump(), club_id=club_id)
        self.db.add(db_activity)
        await self.db.flush()
        await self.db.refresh(db_activity)
        return db_activity


class ClubActivityCreateRequestRepository(
    RepositoryBase[
        ClubActivityCreateRequest,
        ClubActivityCreateRequestCreate,
        RequestModerate,
    ],
):
    model = ClubActivityCreateRequest

    async def count_pending(self) -> int:
        """Count pending requests in SQL.

        A COUNT query rather than loading the rows and taking len(): this exists to
        make the navigation badge cheap, so materialising every pending request in
        Python would defeat the point.
        """
        stmt = select(func.count()).select_from(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def get_pending_requests(self) -> Page[ClubActivityCreateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[ClubActivityCreateRequest]", await apaginate(self.db, stmt))


class ClubActivityUpdateRequestRepository(
    RepositoryBase[
        ClubActivityUpdateRequest,
        ClubActivityUpdateRequestCreate,
        RequestModerate,
    ],
):
    model = ClubActivityUpdateRequest

    async def count_pending(self) -> int:
        """Count pending requests in SQL.

        A COUNT query rather than loading the rows and taking len(): this exists to
        make the navigation badge cheap, so materialising every pending request in
        Python would defeat the point.
        """
        stmt = select(func.count()).select_from(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def get_pending_requests(self) -> Page[ClubActivityUpdateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[ClubActivityUpdateRequest]", await apaginate(self.db, stmt))

    async def supersede_pending_requests_by_activity(
        self,
        club_activity_id: int,
    ) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.moderation_status == ModerationStatusEnum.pending,
                self.model.club_activity_id == club_activity_id,
            )
            .values(moderation_status=ModerationStatusEnum.superseded)
        )
        await self.db.execute(stmt)
        await self.db.flush()
