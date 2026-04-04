from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.club import Club
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubMemberUpdate, ClubUpdate
from app.services.base import ServiceBase
from app.services.errors import DuplicateClubNameError
from app.utils.sqlalchemy import get_upsert_insert


class ClubService(ServiceBase[Club, ClubCreate, ClubUpdate]):
    model = Club

    async def create(self, obj_in: ClubCreate) -> Club:
        try:
            return await super().create(obj_in)
        except IntegrityError as exc:
            raise DuplicateClubNameError from exc

    async def get_by_name(self, name: str) -> Sequence[Club]:
        result = await self.db.execute(select(Club).where(Club.name == name))
        return result.scalars().all()

    async def list(self, offset: int, limit: int) -> Sequence[Club]:
        result = await self.db.execute(select(Club).offset(offset).limit(limit))
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
        stmt = get_upsert_insert(self.db, self.model).values(
            user_id=user.id,
            club_id=club.id,
            membership=membership,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[self.model.club_id, self.model.user_id],
            set_={"membership": membership},
        ).returning(self.model)
        result = await self.db.scalars(stmt)
        return result.first()
