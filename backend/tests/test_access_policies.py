from types import SimpleNamespace
from typing import cast

import pytest

from app.models.club import Club
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.services.errors import ResourceForbiddenError
from app.services.policies import AccessPolicy


def make_user(role: RoleEnum) -> User:
    return cast("User", SimpleNamespace(id=1, role=role))


def test_federation_staff_inherits_moderator_access() -> None:
    AccessPolicy.ensure_role_allowed(
        make_user(RoleEnum.federation_staff),
        [RoleEnum.moderator],
    )


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
def test_admin_and_dev_have_admin_access(role: RoleEnum) -> None:
    AccessPolicy.ensure_role_allowed(make_user(role), [RoleEnum.admin])


@pytest.mark.parametrize("role", [RoleEnum.admin, RoleEnum.dev])
def test_admin_and_dev_have_no_moderator_only_access(role: RoleEnum) -> None:
    with pytest.raises(ResourceForbiddenError) as exc_info:
        AccessPolicy.ensure_role_allowed(make_user(role), [RoleEnum.moderator])

    assert exc_info.value.error_code == "ROLE_NOT_ALLOWED"


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
