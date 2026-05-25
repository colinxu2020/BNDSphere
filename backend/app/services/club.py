from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import User
from app.schemas.club import AdminClubUpdate, ClubCreate, ClubMemberUpdate
from app.schemas.moderations.club import ClubUpdateRequestCreate
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.services.base import ServiceBase
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicatePendingRequestError,
    ResourceForbiddenError,
)


class ClubService(ServiceBase[Club, ClubCreate, AdminClubUpdate]):
    model = Club

    async def create(self, obj_in: ClubCreate, **kwargs: object) -> Club:
        try:
            return await super().create(obj_in, **kwargs)
        except IntegrityError as exc:
            raise DuplicateClubNameError from exc

    async def ensure_club_normal(self, club_id: int) -> Club:
        club = await self.get(club_id)
        if club is None:
            raise ClubNotFoundError(club_id) from None
        if club.status != ClubStatusEnum.normal:
            raise ResourceForbiddenError(
                "error.club.not_active",
                "CLUB_NOT_ACTIVE",
                {"club_id": club_id},
            ) from None
        return club

    async def get_by_name(self, name: str) -> Sequence[Club]:
        result = await self.db.execute(select(Club).where(Club.name == name))
        return result.scalars().all()

    async def get_multi(
        self,
        search: str | None = None,
        category: ClubCategoryEnum | None = None,
        status: ClubStatusEnum | None = None,
    ) -> Page[Club]:
        stmt = select(Club)
        if search is not None and search.strip():
            score_func = (
                func.similarity(Club.name, search) * 1.0
                + func.similarity(Club.summary, search) * 0.5
                + func.similarity(Club.description, search) * 0.3
            )
            stmt = (
                select(Club, score_func)
                .where(
                    or_(
                        Club.name.bool_op("%")(search),
                        Club.summary.bool_op("%")(search),
                        Club.description.bool_op("%")(search),
                    ),
                )
                .order_by(score_func.desc())
            )
        else:
            stmt = stmt.order_by(self.model.id.desc())

        if category is not None:
            stmt = stmt.where(Club.category == category)
        if status is not None:
            stmt = stmt.where(Club.status == status)

        return cast("Page[Club]", await apaginate(self.db, stmt))


class ClubMemberService(ServiceBase[ClubMember, ClubMemberUpdate, ClubMemberUpdate]):
    model = ClubMember

    async def get_by_club_user(self, club: Club, user: User) -> ClubMember | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.user_id == user.id,
                self.model.club_id == club.id,
            ),
        )
        return result.scalars().first()

    async def set_relationship(
        self,
        club: Club,
        user: User,
        membership: ClubMembershipEnum,
    ) -> ClubMember:
        stmt = (
            insert(self.model)
            .on_conflict_do_update(
                index_elements=[self.model.club_id, self.model.user_id],
                set_={"membership": membership},
            )
            .values(user_id=user.id, club_id=club.id, membership=membership)
            .returning(self.model)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()


class ClubUpdateRequestService(
    ServiceBase[
        ClubUpdateRequest,
        ClubUpdateRequestCreate,
        RequestModerate,
    ],
):
    model = ClubUpdateRequest

    async def get_pending_requests(self) -> Page[ClubUpdateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[ClubUpdateRequest]", await apaginate(self.db, stmt))

    async def moderate_request(
        self,
        request: ClubUpdateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubUpdateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )

    async def supersede_pending_requests_by_club(self, club_id: int) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.moderation_status == ModerationStatusEnum.pending,
                self.model.club_id == club_id,
            )
            .values(moderate_status=ModerationStatusEnum.superseded)
        )
        try:
            await self.db.execute(stmt)
            await self.db.flush()
        except IntegrityError:
            raise DuplicatePendingRequestError from None
