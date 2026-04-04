from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.club import Club
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubMemberUpdate, ClubUpdate
from app.services.base import ServiceBase


class ClubService(ServiceBase[Club, ClubCreate, ClubUpdate]):
    model = Club

    async def get_by_name(self, name: str) -> Sequence[Club]:
        result = await self.db.execute(select(Club).where(Club.name == name))
        return result.scalars().all()


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
        try:
            async with self.db.begin_nested():
                new_relationship = self.model(
                    user_id=user.id,
                    club_id=club.id,
                    membership=membership,
                )
                self.db.add(new_relationship)
                await self.db.flush()
                return new_relationship
        except IntegrityError:
            pass

        stmt = (
            select(self.model)
            .where(
                self.model.user_id == user.id,
                self.model.club_id == club.id,
            )
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        relationship = result.scalars().first()
        if relationship is None:
            return await self.set_relationship(club, user, membership)
        relationship.membership = membership
        await self.db.flush()
        return relationship
