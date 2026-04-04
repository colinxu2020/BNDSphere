from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate, ClubMemberUpdate, ClubUpdate
from app.schemas.generic import PageResponse
from app.services.base import ServiceBase
from app.services.errors import DuplicateClubNameError
from app.utils.sqlalchemy import get_dialect, get_upsert_insert


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

    async def get_multi(
        self,
        offset: int,
        limit: int,
        search: str | None = None,
        category: ClubCategoryEnum | None = None,
    ) -> PageResponse[Sequence[Club]]:
        if search is not None:
            if get_dialect(self.db) == "postgresql":
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
                stmt = (
                    select(Club)
                    .where(
                        or_(
                            Club.name.contains(search),
                            Club.summary.contains(search),
                            Club.description.contains(search),
                        ),
                    )
                    .order_by(self.model.id.desc())
                )
        else:
            stmt = select(Club).order_by(self.model.id.desc())
        if category is not None:
            stmt = stmt.where(Club.category == category)
        stmt = stmt.where(Club.status == ClubStatusEnum.normal)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        count = count_result.scalar_one()
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return PageResponse(total=count, items=result.scalars().all())


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
