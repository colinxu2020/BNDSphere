from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import Club, GeneralActivity
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivityLevelEnum,
)
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityUpdate,
    GeneralActivityCreate,
    GeneralActivityUpdate,
)
from app.services.base import ServiceBase
from app.services.errors import BusinessError


class GeneralActivityService(
    ServiceBase[GeneralActivity, GeneralActivityCreate, GeneralActivityUpdate],
):
    model = GeneralActivity

    async def get_multi(
        self,
        search: str | None = None,
        level: GeneralActivityLevelEnum | None = None,
    ) -> Sequence[GeneralActivity]:
        stmt = select(self.model).order_by(GeneralActivity.created_at.desc())
        if level is not None:
            stmt = stmt.where(self.model.level == level)
        if search is not None:
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
        result = await self.db.execute(stmt)
        return result.scalars().all()


class ClubGeneralActivityService(
    ServiceBase[
        ClubGeneralActivityRecord,
        ClubGeneralActivityCreate,
        ClubGeneralActivityUpdate,
    ],
):
    model = ClubGeneralActivityRecord

    async def create_club_general_activity(
        self,
        obj_in: ClubGeneralActivityCreate,
        club_id: int,
    ) -> ClubGeneralActivityRecord:
        try:
            stmt = select(self.model).where(
                self.model.club_id == club_id,
                self.model.activity_id == obj_in.activity_id,
            )
            existing = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise BusinessError(
                    message="the club already participate in the activity",
                    status=409,
                )
            return await self.create(obj_in, club_id=club_id)
        except IntegrityError:
            raise BusinessError(
                message="database conflict",
                status=409,
            ) from None
        except OperationalError:
            raise BusinessError(
                message="database cannot respond",
                status=503,
            ) from None

    async def get_by_club(self, club: Club) -> Sequence[ClubGeneralActivityRecord]:
        stmt = select(self.model).where(self.model.club == club)
        result = await self.db.execute(stmt)
        return result.scalars().all()
