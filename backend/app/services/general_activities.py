from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import Club, GeneralActivity, User
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivityLevelEnum,
)
from app.schemas.club import ScfClubUpdate
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityUpdate,
    GeneralActivityCreate,
    GeneralActivityUpdate,
)
from app.services.base import ServiceBase
from app.services.errors import (
    BusinessError,
    DuplicateResourceError,
    GeneralActivityNotFoundError,
    ResourceNotFoundError,
)


class GeneralActivityService(
    ServiceBase[GeneralActivity, GeneralActivityCreate, GeneralActivityUpdate],
):
    model = GeneralActivity

    async def get_multi(
        self,
        search: str | None = None,
        level: GeneralActivityLevelEnum | None = None,
    ) -> Page[GeneralActivity]:
        stmt = select(self.model).order_by(GeneralActivity.created_at.desc())
        if level is not None:
            stmt = stmt.where(self.model.level == level)
        if search is not None:
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
        return await apaginate(self.db, stmt)


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
                raise DuplicateResourceError(
                    message_key="error.general_activity.club_requested",
                    error_code="DUPLICATE_CLUB_REQUESTED",
                    details={
                        "club_id": club_id,
                        "activity_id": obj_in.activity_id,
                    },
                )
            return await self.create(obj_in, club_id=club_id)
        except IntegrityError:
            raise BusinessError(
                message_key="error.database.conflict",
                status_code=409,
                error_code="DATABASE_CONFLICT",
            ) from None
        except OperationalError:
            raise BusinessError(
                message_key="error.database.unavailable",
                status_code=503,
                error_code="DATABASE_UNAVAILABLE",
            ) from None

    async def get_by_club(self, club: Club) -> Page[ClubGeneralActivityRecord]:
        stmt = select(self.model).where(self.model.club == club)
        return await apaginate(self.db, stmt)

    async def get_by_club_activity(
        self,
        club: Club,
        activity: GeneralActivity,
    ) -> ClubGeneralActivityRecord:
        stmt = select(self.model).where(
            self.model.club == club,
            self.model.activity_id == activity.id,
        )
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        if result is None:
            raise GeneralActivityNotFoundError(activity.id) from None
        return result

    async def review_record(
        self,
        record_id: int,
        obj_in: ScfClubUpdate,
        auditor: User,
    ) -> ClubGeneralActivityRecord:
        db_obj = await self.get(record_id)
        if db_obj is None:
            raise ResourceNotFoundError(
                "error.general_activity.record_not_found",
                "RECORD_NOT_FOUND",
                {"record_id": record_id},
            )

        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db_obj.auditor = auditor
        db_obj.auditor_id = auditor.id

        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
