from collections.abc import Sequence
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubMemberUpdate, ClubUpdate
from app.services.base import ServiceBase
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    ResourceForbiddenError,
)
from app.utils.crud_utils import apply_fulltext_search, get_dialect, get_upsert_insert


class ClubService(ServiceBase[Club, ClubCreate, ClubUpdate]):
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
            dialect = get_dialect(self.db)
            search_fields = {
                Club.name: 1.0,
                Club.summary: 0.5,
                Club.description: 0.3,
            }
            stmt = apply_fulltext_search(
                stmt=stmt,
                dialect=dialect,
                search=search,
                search_fields=search_fields,
                default_order_by=self.model.id.desc(),
            )
        else:
            stmt = stmt.order_by(self.model.id.desc())

        if category is not None:
            stmt = stmt.where(Club.category == category)
        if status is not None:
            stmt = stmt.where(Club.status == status)

        return await apaginate(self.db, stmt)


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
        stmt = get_upsert_insert(
            self.db,
            self.model,
            [self.model.club_id, self.model.user_id],
            {"membership": membership},
        )
        stmt = stmt.values(user_id=user.id, club_id=club.id, membership=membership)
        await self.db.execute(stmt)
        return cast("ClubMember", await self.get_by_club_user(club, user))
