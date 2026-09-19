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
