from collections.abc import Sequence
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import Row, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import User
from app.repositories.base import RepositoryBase
from app.schemas.club import (
    AdminClubUpdate,
    ClubCreate,
    ClubMemberUpdate,
    ClubSummaryInfo,
)
from app.schemas.moderations.club import ClubUpdateRequestCreate
from app.schemas.moderations.moderation_common import RequestModerate


class ClubRepository(RepositoryBase[Club, ClubCreate, AdminClubUpdate]):
    model = Club

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

    async def get_multi_summary(
        self,
        search: str | None = None,
        category: ClubCategoryEnum | None = None,
        status: ClubStatusEnum | None = None,
    ) -> Page[ClubSummaryInfo]:
        """Club rows plus a member count, without loading the members.

        The count is a correlated scalar subquery evaluated by Postgres per row, so
        the database returns one integer per club. Loading Club.members and taking
        len() in Python would only move the original inefficiency behind the API.
        """
        member_count = (
            select(func.count(ClubMember.id))
            .where(ClubMember.club_id == Club.id)
            .correlate(Club)
            .scalar_subquery()
            .label("member_count")
        )

        if search is not None and search.strip():
            score_func = (
                func.similarity(Club.name, search) * 1.0
                + func.similarity(Club.summary, search) * 0.5
                + func.similarity(Club.description, search) * 0.3
            )
            stmt = (
                select(Club, member_count)
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
            stmt = select(Club, member_count).order_by(Club.id.desc())

        if category is not None:
            stmt = stmt.where(Club.category == category)
        if status is not None:
            stmt = stmt.where(Club.status == status)

        def to_summary(
            rows: Sequence[Row[tuple[Club, int]]],
        ) -> list[ClubSummaryInfo]:
            return [
                ClubSummaryInfo(
                    id=club.id,
                    name=club.name,
                    category=club.category,
                    summary=club.summary,
                    description=club.description,
                    logo_uri=club.logo_uri,
                    created_at=club.created_at,
                    status=club.status,
                    star_level=club.star_level,
                    member_count=member_count,
                )
                for club, member_count in rows
            ]

        return cast(
            "Page[ClubSummaryInfo]",
            await apaginate(self.db, stmt, transformer=to_summary),
        )


class ClubMemberRepository(
    RepositoryBase[ClubMember, ClubMemberUpdate, ClubMemberUpdate],
):
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


class ClubUpdateRequestRepository(
    RepositoryBase[
        ClubUpdateRequest,
        ClubUpdateRequestCreate,
        RequestModerate,
    ],
):
    model = ClubUpdateRequest

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

    async def get_pending_requests(self) -> Page[ClubUpdateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[ClubUpdateRequest]", await apaginate(self.db, stmt))

    async def supersede_pending_requests_by_club(self, club_id: int) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.moderation_status == ModerationStatusEnum.pending,
                self.model.club_id == club_id,
            )
            .values(moderation_status=ModerationStatusEnum.superseded)
        )
        await self.db.execute(stmt)
        await self.db.flush()
