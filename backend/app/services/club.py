from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club, ClubStarLevelEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubUserMembershipEnum
from app.models.user import User
from app.schemas.club import ClubCreate


async def get_club_by_club_id(db: AsyncSession, club_id: int) -> Club | None:
    return await db.get(Club, club_id)


async def get_clubs_by_club_name(db: AsyncSession, name: str) -> Sequence[Club]:
    result = await db.execute(select(Club).where(Club.name == name))
    return result.scalars().all()


async def create_club(club: ClubCreate, db: AsyncSession) -> Club:
    db_club = Club(
        name=club.name,
        summary=club.summary,
        description=club.description,
        status=ClubStatusEnum.unreviewed,
        star_level=ClubStarLevelEnum.none,
    )
    db.add(db_club)
    await db.commit()
    await db.refresh(db_club)
    return db_club


async def set_club_relationship(
    db: AsyncSession,
    club: Club,
    user: User,
    relationship: ClubUserMembershipEnum,
) -> ClubMember:
    stmt = select(ClubMember).where(
        ClubMember.club_id == club.id,
        ClubMember.user_id == user.club_id,
    )
    result = await db.execute(stmt)
    record: ClubMember = result.scalars().first()
    if record is not None:
        record.membership = relationship
    else:
        record = ClubMember(
            club_id=club.id,
            user_id=user.id,
            membership=relationship,
        )
        db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
