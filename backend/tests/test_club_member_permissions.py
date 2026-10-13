"""Service authorization and presidency transfers, using in-memory members."""

from unittest.mock import Mock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.repositories.club import ClubMemberRepository, ClubRepository
from app.schemas.club import ClubMemberRoleUpdate
from app.services.club import ClubService
from app.services.errors import ResourceForbiddenError


def _service(
    role: RoleEnum,
) -> tuple[ClubService, User, ClubMember, ClubMember, Mock]:
    president = ClubMember(
        id=1, club_id=1, user_id=1, membership=ClubMembershipEnum.president
    )
    target = ClubMember(
        id=2, club_id=1, user_id=2, membership=ClubMembershipEnum.member
    )
    club = Club(
        id=1, status=ClubStatusEnum.normal, claimed=True, members=[president, target]
    )
    actor = User(id=1 if role == RoleEnum.user else 9, role=role)
    repository = Mock(spec=ClubRepository)
    repository.db = Mock(spec=AsyncSession)
    repository.db.info = {}
    repository.db.in_transaction.return_value = False
    repository.get_with_lock.return_value = club
    members = Mock(spec=ClubMemberRepository)
    members.get_by_club_user.return_value = president if role == RoleEnum.user else None
    members.get_by_club_user_id.return_value = target
    members.count_vice_presidents.return_value = 0

    async def set_membership(
        member: ClubMember, membership: ClubMembershipEnum
    ) -> ClubMember:
        member.membership = membership
        return member

    members.set_membership.side_effect = set_membership
    return ClubService(repository, members), actor, president, target, members


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev, RoleEnum.user])
async def test_member_role_changes_and_removal(role: RoleEnum) -> None:
    service, actor, president, target, members = _service(role)
    for membership in ["vice_president", "member"]:
        result = await service.update_member_role(
            1,
            target.user_id,
            ClubMemberRoleUpdate.model_validate({"membership": membership}),
            actor,
        )
        assert result.membership == membership
    await service.remove_member(1, target.user_id, actor)
    assert target.membership == ClubMembershipEnum.left
    assert president.membership == ClubMembershipEnum.president
    assert members.set_membership.await_count == 3
    assert service.repository.get_with_lock.return_value.claimed is True


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev, RoleEnum.user])
async def test_transfer_demotes_the_clubs_president(role: RoleEnum) -> None:
    service, actor, president, target, members = _service(role)
    await service.update_member_role(
        1,
        target.user_id,
        ClubMemberRoleUpdate.model_validate({"membership": "president"}),
        actor,
    )
    assert president.membership == ClubMembershipEnum.member
    assert target.membership == ClubMembershipEnum.president
    assert service.repository.get_with_lock.return_value.claimed is True
    assert members.set_membership.await_args_list == [
        call(president, ClubMembershipEnum.member),
        call(target, ClubMembershipEnum.president),
    ]


async def test_president_cannot_demote_or_remove_themselves() -> None:
    service, actor, president, _, members = _service(RoleEnum.user)
    members.get_by_club_user_id.return_value = president
    with pytest.raises(ResourceForbiddenError, match="CANNOT_CHANGE_PRESIDENT_ROLE"):
        await service.update_member_role(
            1,
            president.user_id,
            ClubMemberRoleUpdate.model_validate({"membership": "member"}),
            actor,
        )
    with pytest.raises(ResourceForbiddenError, match="CANNOT_REMOVE_PRESIDENT"):
        await service.remove_member(1, president.user_id, actor)
    members.set_membership.assert_not_awaited()
    assert service.repository.get_with_lock.return_value.claimed is True


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
@pytest.mark.parametrize("remove", [False, True])
async def test_bypass_can_dismiss_president_and_unclaim_club(
    role: RoleEnum, *, remove: bool
) -> None:
    service, actor, president, target, members = _service(role)
    members.get_by_club_user_id.return_value = president
    if remove:
        await service.remove_member(1, president.user_id, actor)
    else:
        await service.update_member_role(
            1,
            president.user_id,
            ClubMemberRoleUpdate.model_validate({"membership": "member"}),
            actor,
        )
    assert president.membership == (
        ClubMembershipEnum.left if remove else ClubMembershipEnum.member
    )
    assert target.membership == ClubMembershipEnum.member
    assert service.repository.get_with_lock.return_value.claimed is False
    members.set_membership.assert_awaited_once()

    members.get_by_club_user_id.return_value = target
    await service.update_member_role(
        1,
        target.user_id,
        ClubMemberRoleUpdate.model_validate({"membership": "president"}),
        actor,
    )
    assert target.membership == ClubMembershipEnum.president
    assert service.repository.get_with_lock.return_value.claimed is True


@pytest.mark.parametrize("status", [ClubStatusEnum.unreviewed, ClubStatusEnum.archived])
async def test_admin_can_dismiss_president_of_inactive_club(
    status: ClubStatusEnum,
) -> None:
    service, actor, president, _, members = _service(RoleEnum.admin)
    service.repository.get_with_lock.return_value.status = status
    members.get_by_club_user_id.return_value = president
    await service.remove_member(1, president.user_id, actor)
    assert president.membership == ClubMembershipEnum.left
    assert service.repository.get_with_lock.return_value.claimed is False


@pytest.mark.parametrize(
    "role", [RoleEnum.user, RoleEnum.moderator, RoleEnum.federation_staff, RoleEnum.ban]
)
async def test_roles_without_bypass_still_require_presidency(role: RoleEnum) -> None:
    service, actor, _, target, members = _service(role)
    members.get_by_club_user.return_value = None
    error = "USER_BANNED" if role == RoleEnum.ban else "CLUB_PRESIDENT_REQUIRED"
    with pytest.raises(ResourceForbiddenError, match=error):
        await service.remove_member(1, target.user_id, actor)
    members.set_membership.assert_not_awaited()
