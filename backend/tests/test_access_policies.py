from types import SimpleNamespace
from typing import cast

import pytest

from app.models.club import Club
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.services.errors import ResourceForbiddenError
from app.services.policies import AccessPolicy


def make_user(role: RoleEnum) -> User:
    return cast("User", SimpleNamespace(id=1, role=role))


@pytest.mark.parametrize(
    ("role", "permitted"),
    [
        (RoleEnum.ban, set()),
        (RoleEnum.user, {RoleEnum.user}),
        (RoleEnum.moderator, {RoleEnum.moderator}),
        (RoleEnum.federation_staff, {RoleEnum.federation_staff, RoleEnum.moderator}),
        (RoleEnum.admin, set(RoleEnum)),
        (RoleEnum.dev, set(RoleEnum)),
    ],
)
@pytest.mark.parametrize("required", list(RoleEnum))
def test_global_role_access_matrix(
    role: RoleEnum, permitted: set[RoleEnum], required: RoleEnum
) -> None:
    if required in permitted:
        AccessPolicy.ensure_role_allowed(make_user(role), [required])
    else:
        with pytest.raises(ResourceForbiddenError) as exc_info:
            AccessPolicy.ensure_role_allowed(make_user(role), [required])
        assert exc_info.value.error_code == (
            "USER_BANNED" if role == RoleEnum.ban else "ROLE_NOT_ALLOWED"
        )


@pytest.mark.parametrize("role", list(RoleEnum))
def test_empty_role_allowlist_preserves_global_bypass(role: RoleEnum) -> None:
    if role in (RoleEnum.admin, RoleEnum.dev):
        AccessPolicy.ensure_role_allowed(make_user(role), [])
    else:
        with pytest.raises(ResourceForbiddenError):
            AccessPolicy.ensure_role_allowed(make_user(role), [])


@pytest.mark.parametrize("role", list(RoleEnum))
@pytest.mark.parametrize("membership_role", [None, *ClubMembershipEnum])
def test_club_access_requires_membership_unless_globally_privileged(
    role: RoleEnum, membership_role: ClubMembershipEnum | None
) -> None:
    membership = (
        ClubMember(user_id=1, club_id=1, membership=membership_role)
        if membership_role is not None
        else None
    )
    club = Club(id=1)
    if role != RoleEnum.ban and (
        role in (RoleEnum.admin, RoleEnum.dev)
        or membership_role == ClubMembershipEnum.president
    ):
        AccessPolicy.ensure_club_role_allowed(
            make_user(role), club, membership, [ClubMembershipEnum.president]
        )
    else:
        with pytest.raises(ResourceForbiddenError) as exc_info:
            AccessPolicy.ensure_club_role_allowed(
                make_user(role), club, membership, [ClubMembershipEnum.president]
            )
        assert exc_info.value.error_code == (
            "USER_BANNED" if role == RoleEnum.ban else "CLUB_ROLE_NOT_ALLOWED"
        )


def test_federation_staff_inherits_moderator_access() -> None:
    AccessPolicy.ensure_role_allowed(
        make_user(RoleEnum.federation_staff),
        [RoleEnum.moderator],
    )


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
def test_admin_and_dev_have_admin_access(role: RoleEnum) -> None:
    AccessPolicy.ensure_role_allowed(make_user(role), [RoleEnum.admin])


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
def test_admin_and_dev_have_unrestricted_access(role: RoleEnum) -> None:
    AccessPolicy.ensure_role_allowed(make_user(role), [RoleEnum.moderator])


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
def test_admin_and_dev_have_club_management_access(role: RoleEnum) -> None:
    AccessPolicy.ensure_club_role_allowed(
        make_user(role),
        cast("Club", SimpleNamespace(id=1)),
        None,
        [ClubMembershipEnum.president],
    )


def test_regular_user_has_no_implicit_club_management_access() -> None:
    with pytest.raises(ResourceForbiddenError) as exc_info:
        AccessPolicy.ensure_club_role_allowed(
            make_user(RoleEnum.user),
            cast("Club", SimpleNamespace(id=1)),
            None,
            [ClubMembershipEnum.president],
        )

    assert exc_info.value.error_code == "CLUB_ROLE_NOT_ALLOWED"
