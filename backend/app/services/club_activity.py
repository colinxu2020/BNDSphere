from datetime import UTC, datetime
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import Club, User
from app.models.club_activity import ClubActivity
from app.models.moderations.club_activity import (
    ClubActivityCreateRequest,
    ClubActivityUpdateRequest,
)
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.schemas.club_activity import ClubActivityCreate, ClubActivityUpdate
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreate,
    ClubActivityUpdateRequestCreate,
)
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.services.base import ServiceBase
from app.services.errors import DuplicatePendingRequestError


class ClubActivityService(
    ServiceBase[ClubActivity, ClubActivityCreate, ClubActivityUpdate],
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


class ClubActivityCreateRequestService(
    ServiceBase[
        ClubActivityCreateRequest,
        ClubActivityCreateRequestCreate,
        RequestModerate,
    ],
):
    model = ClubActivityCreateRequest

    async def get_pending_requests(self) -> Page[ClubActivityCreateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[ClubActivityCreateRequest]", await apaginate(self.db, stmt))

    async def moderate_request(
        self,
        request: ClubActivityCreateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubActivityCreateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )


class ClubActivityUpdateRequestService(
    ServiceBase[
        ClubActivityUpdateRequest,
        ClubActivityUpdateRequestCreate,
        RequestModerate,
    ],
):
    model = ClubActivityUpdateRequest

    async def get_pending_requests(self) -> Page[ClubActivityUpdateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[ClubActivityUpdateRequest]", await apaginate(self.db, stmt))

    async def moderate_request(
        self,
        request: ClubActivityUpdateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubActivityUpdateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )

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
        try:
            await self.db.execute(stmt)
            await self.db.flush()
        except IntegrityError:
            raise DuplicatePendingRequestError from None
