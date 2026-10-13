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
    club = Club(id=1, status=ClubStatusEnum.normal, members=[president, target])
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
    assert members.set_membership.await_args_list == [
        call(president, ClubMembershipEnum.member),
        call(target, ClubMembershipEnum.president),
    ]


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
async def test_bypass_cannot_demote_or_remove_the_current_president(
    role: RoleEnum,
) -> None:
    service, actor, president, _, members = _service(role)
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
