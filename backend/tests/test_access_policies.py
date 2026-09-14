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


@pytest.mark.parametrize("allowed_role", [RoleEnum.admin, RoleEnum.moderator])
def test_dev_has_no_implicit_privileged_access(allowed_role: RoleEnum) -> None:
    with pytest.raises(ResourceForbiddenError) as exc_info:
        AccessPolicy.ensure_role_allowed(make_user(RoleEnum.dev), [allowed_role])

    assert exc_info.value.error_code == "ROLE_NOT_ALLOWED"


def test_dev_has_no_implicit_club_management_access() -> None:
    club = cast("Club", SimpleNamespace(id=1))

    with pytest.raises(ResourceForbiddenError) as exc_info:
        AccessPolicy.ensure_club_role_allowed(
            make_user(RoleEnum.dev),
            club,
            None,
            [ClubMembershipEnum.president],
        )

    assert exc_info.value.error_code == "CLUB_ROLE_NOT_ALLOWED"


def test_admin_keeps_implicit_club_management_access() -> None:
    AccessPolicy.ensure_club_role_allowed(
        make_user(RoleEnum.admin),
        cast("Club", SimpleNamespace(id=1)),
        None,
        [ClubMembershipEnum.president],
    )
