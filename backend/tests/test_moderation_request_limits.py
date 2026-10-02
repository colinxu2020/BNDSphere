"""Update requests must enforce the same length limits the approval schema does.

Otherwise a request is accepted at creation and then 500s when a moderator
approves it (AdminClubUpdate / AdminUserUpdate reject the stored value).
"""

import pytest
from pydantic import ValidationError

from app.core import constants
from app.schemas.moderations.club import ClubUpdateRequestCreatePublic
from app.schemas.moderations.user_update_request import UserUpdateRequestCreate


def test_club_update_request_rejects_overlong_description() -> None:
    limit = constants.CLUB_MAX_DESCRIPTION_LENGTH
    ClubUpdateRequestCreatePublic(description="x" * limit)
    with pytest.raises(ValidationError):
        ClubUpdateRequestCreatePublic(description="x" * (limit + 1))
    with pytest.raises(ValidationError):
        ClubUpdateRequestCreatePublic(
            summary="x" * (constants.CLUB_MAX_SUMMARY_LENGTH + 1),
        )


def test_user_update_request_rejects_overlong_fields() -> None:
    UserUpdateRequestCreate(description="x" * constants.USER_MAX_DESCRIPTION_LENGTH)
    with pytest.raises(ValidationError):
        UserUpdateRequestCreate(
            description="x" * (constants.USER_MAX_DESCRIPTION_LENGTH + 1),
        )
    with pytest.raises(ValidationError):
        UserUpdateRequestCreate(username="x" * (constants.USER_MAX_USERNAME_LENGTH + 1))


@pytest.mark.parametrize("username", ["", "   "])
def test_user_update_request_rejects_a_blank_username(username: str) -> None:
    with pytest.raises(ValidationError):
        UserUpdateRequestCreate(username=username)


def test_user_update_request_strips_username_like_admin_update() -> None:
    # Approval replays the stored request through AdminUserUpdate, so both
    # schemas must agree on what a valid username is.
    assert UserUpdateRequestCreate(username="  bob  ").username == "bob"
