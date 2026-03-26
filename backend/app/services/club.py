from collections.abc import Sequence

from sqlalchemy import select

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
        relationship = await self.get_by_club_user(club, user)
        if relationship is None:
            relationship = await self.create(
                ClubMemberUpdate(user.id, club.id, membership),
            )
        else:
            relationship.membership = membership
            self.db.add(relationship)
            await self.db.commit()
            await self.db.refresh(relationship)
        return relationship
