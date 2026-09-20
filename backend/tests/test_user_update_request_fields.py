"""Profile update requests must carry only the fields the user actually changed.

The frontend used to send every field on every submit, with ``null``/``""``
standing in for "unchanged". Both shapes are rejected here, and even if they
were not, ``update_fields`` would replay the placeholders and wipe the values
the user never touched.
"""

import pytest
from pydantic import ValidationError

from app.schemas.moderations.user_update_request import UserUpdateRequestCreate
from app.services.errors import BadRequestError
from app.services.moderation_payload import requested_update_fields


def test_username_only_request_touches_only_username() -> None:
    request = UserUpdateRequestCreate(username="new-name")
    assert requested_update_fields(request) == ["username"]


def test_empty_string_placeholder_for_avatar_is_rejected() -> None:
    with pytest.raises(ValidationError):
        UserUpdateRequestCreate(username="new-name", avatar_uri="")


def test_null_placeholder_for_unchanged_description_is_rejected() -> None:
    with pytest.raises(BadRequestError):
        UserUpdateRequestCreate(username="new-name", description=None)
