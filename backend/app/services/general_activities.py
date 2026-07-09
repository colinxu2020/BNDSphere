from datetime import datetime

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import Club, GeneralActivity, User
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivityLevelEnum,
)
from app.repositories.general_activities import (
    ClubGeneralActivityRepository,
    GeneralActivityRepository,
)
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityUpdate,
    FederationRecordUpdate,
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
    ServiceBase[
        GeneralActivity,
        GeneralActivityCreate,
        GeneralActivityUpdate,
    ],
):
    repository: GeneralActivityRepository

    async def get_multi(
        self,
        search: str | None = None,
        level: GeneralActivityLevelEnum | None = None,
        *,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        has_poster: bool | None = None,
    ) -> Page[GeneralActivity]:
        return await self.repository.get_multi(
            search,
            level,
            starts_before=starts_before,
            ends_after=ends_after,
            has_poster=has_poster,
        )


class ClubGeneralActivityService(
    ServiceBase[
        ClubGeneralActivityRecord,
        ClubGeneralActivityCreate,
        ClubGeneralActivityUpdate,
    ],
):
    repository: ClubGeneralActivityRepository

    async def create_club_general_activity(
        self,
        obj_in: ClubGeneralActivityCreate,
        club_id: int,
    ) -> ClubGeneralActivityRecord:
        try:
            async with self.transaction():
                existing = await self.repository.find_by_club_id_and_activity_id(
                    club_id,
                    obj_in.activity_id,
                )
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
        return await self.repository.get_by_club(club)

    async def get_by_club_and_activity(
        self,
        club: Club,
        activity: GeneralActivity,
    ) -> ClubGeneralActivityRecord:
        result = await self.repository.find_by_club_and_activity(club, activity)
        if result is None:
            raise GeneralActivityNotFoundError(activity.id) from None
        return result

    async def review_record(
        self,
        record_id: int,
        obj_in: FederationRecordUpdate,
        auditor: User,
    ) -> ClubGeneralActivityRecord:
        db_obj = await self.get(record_id)
        if db_obj is None:
            raise ResourceNotFoundError(
                "error.general_activity.record_not_found",
                "RECORD_NOT_FOUND",
                {"record_id": record_id},
            )

        async with self.transaction():
            return await self.repository.review_record(db_obj, obj_in, auditor)
