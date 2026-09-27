from collections.abc import Sequence
from datetime import datetime
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import load_only, raiseload, selectinload

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.general_activity import ClubGeneralActivityRecord
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import AuditStatusEnum, User
from app.models.verifications.club_claim import ClubClaimRequest
from app.models.verifications.club_membership import ClubMembershipRequest
from app.models.verifications.verification_common import VerificationStatusEnum
from app.repositories.base import RepositoryBase
from app.schemas.club import ClubCreate, ClubMemberUpdate, ClubUpdate
from app.schemas.moderations.club import ClubUpdateRequestCreate
from app.schemas.moderations.moderation_common import RequestModerate
from app.schemas.verifications.club_claim import ClubClaimRequestCreate
from app.schemas.verifications.club_membership import ClubMembershipRequestCreate
from app.schemas.verifications.verification_common import RequestVerify

# 公开回显只加载「已审核通过」的大型活动参与记录:
# pending/rejected 记录的 proof_files 等内容未经社联审核, 匿名访客不应看到.
_PUBLIC_RECORDS_OPTION = selectinload(
    Club.general_activity_records.and_(
        ClubGeneralActivityRecord.audit_status == AuditStatusEnum.approved,
    ),
)


def _apply_search(stmt: Select[tuple[Club]], search: str | None) -> Select[tuple[Club]]:
    """Trigram 模糊搜索: 命中 name/summary/description 任一, 按加权相似度排序."""
    if search is None or not search.strip():
        return stmt.order_by(Club.id.desc())
    score_func = (
        func.similarity(Club.name, search) * 1.0
        + func.similarity(Club.summary, search) * 0.5
        + func.similarity(Club.description, search) * 0.3
    )
    return stmt.where(
        or_(
            Club.name.bool_op("%")(search),
            Club.summary.bool_op("%")(search),
            Club.description.bool_op("%")(search),
        ),
    ).order_by(score_func.desc())


class ClubRepository(RepositoryBase[Club, ClubCreate, ClubUpdate]):
    model = Club

    async def get_public(self, id_: int) -> Club | None:
        """公开详情读取: general_activity_records 只加载已审核通过的记录."""
        stmt = (
            select(self.model)
            .where(self.model.id == id_)
            .options(_PUBLIC_RECORDS_OPTION)
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def get_by_name(self, name: str) -> Sequence[Club]:
        result = await self.db.execute(select(Club).where(Club.name == name))
        return result.scalars().all()

    async def get_status(self, club_id: int) -> ClubStatusEnum | None:
        result = await self.db.execute(select(Club.status).where(Club.id == club_id))
        return result.scalars().first()

    async def get_multi(
        self,
        search: str | None = None,
        category: ClubCategoryEnum | None = None,
        status: ClubStatusEnum | None = None,
        *,
        public_only: bool = False,
    ) -> Page[Club]:
        if public_only and (search is None or not search.strip()):
            stmt = select(Club).order_by(
                (Club.description != "").desc(),
                Club.star_level.desc(),
                Club.id.asc(),
            )
        else:
            stmt = _apply_search(select(Club), search)

        if public_only:
            stmt = stmt.options(_PUBLIC_RECORDS_OPTION)
        if category is not None:
            stmt = stmt.where(Club.category == category)
        if status is not None:
            stmt = stmt.where(Club.status == status)

        return cast("Page[Club]", await apaginate(self.db, stmt))

    async def get_refs(
        self,
        search: str | None = None,
        status: ClubStatusEnum | None = None,
    ) -> Page[Club]:
        """Ref 档列表: 只取 id/name 两列, 不装载任何关系集合."""
        stmt = _apply_search(select(Club), search).options(
            load_only(Club.id, Club.name),
            raiseload("*"),
        )
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

    async def get_user_ids_with_membership(
        self,
        club_id: int,
        user_ids: Sequence[int],
        allowed_memberships: Sequence[ClubMembershipEnum],
    ) -> set[int]:
        if not user_ids:
            return set()
        result = await self.db.execute(
            select(self.model.user_id).where(
                self.model.club_id == club_id,
                self.model.user_id.in_(user_ids),
                self.model.membership.in_(allowed_memberships),
            ),
        )
        return set(result.scalars().all())

    async def has_president(self, club_id: int) -> bool:
        result = await self.db.execute(
            select(self.model.id)
            .where(
                self.model.club_id == club_id,
                self.model.membership == ClubMembershipEnum.president,
            )
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

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

    async def reject_pending_requests(
        self,
        club_id: int,
        applicant_id: int,
        verifier_id: int,
        verify_at: datetime,
    ) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.club_id == club_id,
                self.model.applicant_id == applicant_id,
                self.model.verification_status == VerificationStatusEnum.pending,
            )
            .values(
                verification_status=VerificationStatusEnum.rejected,
                verifier_id=verifier_id,
                verify_at=verify_at,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()


class ClubClaimRequestRepository(
    RepositoryBase[
        ClubClaimRequest,
        ClubClaimRequestCreate,
        RequestVerify,
    ],
):
    model = ClubClaimRequest

    async def get_pending_requests(self) -> Page[ClubClaimRequest]:
        stmt = (
            select(self.model)
            .where(self.model.verification_status == VerificationStatusEnum.pending)
            .options(
                selectinload(self.model.club),
                selectinload(self.model.applicant),
            )
            .order_by(self.model.apply_at.asc(), self.model.id.asc())
        )
        return cast("Page[ClubClaimRequest]", await apaginate(self.db, stmt))

    async def reject_other_pending_requests(
        self,
        club_id: int,
        approved_request_id: int,
        verifier_id: int,
        verify_at: datetime,
    ) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.club_id == club_id,
                self.model.id != approved_request_id,
                self.model.verification_status == VerificationStatusEnum.pending,
            )
            .values(
                verification_status=VerificationStatusEnum.rejected,
                verifier_id=verifier_id,
                verify_at=verify_at,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
