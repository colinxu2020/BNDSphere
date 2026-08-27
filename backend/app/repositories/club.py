from collections.abc import Sequence
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import User
from app.models.verifications.club_membership import ClubMembershipRequest
from app.models.verifications.verification_common import VerificationStatusEnum
from app.repositories.base import RepositoryBase
from app.schemas.club import AdminClubUpdate, ClubCreate, ClubMemberUpdate, ClubUpdate
from app.schemas.moderations.club import ClubUpdateRequestCreate
from app.schemas.moderations.moderation_common import RequestModerate
from app.schemas.verifications.club_membership import ClubMembershipRequestCreate
from app.schemas.verifications.verification_common import RequestVerify


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

    async def get_managed_by_user(self, user_id: int) -> Page[Club]:
        stmt = (
            select(Club)
            .join(ClubMember, ClubMember.club_id == Club.id)
            .where(
                ClubMember.user_id == user_id,
                ClubMember.membership.in_(
                    [
                        ClubMembershipEnum.president,
                        ClubMembershipEnum.vice_president,
                    ],
                ),
                Club.status != ClubStatusEnum.archived,
            )
            .order_by(Club.id.desc())
        )
        return cast("Page[Club]", await apaginate(self.db, stmt))

    async def update_details(self, club: Club, obj_in: ClubUpdate) -> Club:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(club, field, value)
        self.db.add(club)
        await self.db.flush()
        await self.db.refresh(club)
        return club


class ClubMemberRepository(
    RepositoryBase[ClubMember, ClubMemberUpdate, ClubMemberUpdate],
):
    model = ClubMember

    async def get_by_club_user(self, club: Club, user: User) -> ClubMember | None:
        return await self.get_by_club_user_id(club.id, user.id)

    async def get_by_club_user_id(
        self,
        club_id: int,
        user_id: int,
    ) -> ClubMember | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.user_id == user_id,
                self.model.club_id == club_id,
            ),
        )
        return result.scalars().first()

    async def set_membership(
        self,
        member: ClubMember,
        membership: ClubMembershipEnum,
    ) -> ClubMember:
        member.membership = membership
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

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


class ClubMembershipRequestRepository(
    RepositoryBase[
        ClubMembershipRequest,
        ClubMembershipRequestCreate,
        RequestVerify,
    ],
):
    model = ClubMembershipRequest

    async def get_pending_requests(self, club_id: int) -> Page[ClubMembershipRequest]:
        stmt = select(self.model).where(
            self.model.verification_status == VerificationStatusEnum.pending,
            self.model.club_id == club_id,
        )
        return cast("Page[ClubMembershipRequest]", await apaginate(self.db, stmt))
