import pytest
from pydantic import BaseModel, ValidationError

from app.core.constants import USER_MAX_USERNAME_LENGTH
from app.schemas.moderations.user_update_request import UserUpdateRequestCreate
from app.schemas.user import AdminUserUpdate, UserCreate

CREATE_PAYLOAD = {
    "password": "secure-password",
    "accepted_privacy_policy": True,
    "accepted_user_agreement": True,
    "accepted_cross_border_transfer": True,
}
SCHEMAS = [
    (UserCreate, CREATE_PAYLOAD),
    (AdminUserUpdate, {}),
    (UserUpdateRequestCreate, {}),
]


@pytest.mark.parametrize(("schema", "payload"), SCHEMAS)
@pytest.mark.parametrize("username", [" HCC", "HCC ", "\tHCC", "HCC\u3000", "   ", ""])
def test_username_writes_reject_boundary_whitespace_or_empty(
    schema: type[BaseModel],
    payload: dict[str, object],
    username: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        schema.model_validate({**payload, "username": username})
    assert error.value.errors()[0]["loc"] == ("username",)


@pytest.mark.parametrize(("schema", "payload"), SCHEMAS)
def test_username_writes_allow_interior_spaces_and_max_length(
    schema: type[BaseModel],
    payload: dict[str, object],
) -> None:
    username = "A " + "x" * (USER_MAX_USERNAME_LENGTH - 2)
    assert schema.model_validate({**payload, "username": username}).username == username
