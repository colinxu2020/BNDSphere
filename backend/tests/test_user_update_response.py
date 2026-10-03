from datetime import UTC, datetime

from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.moderations.user_update_request import UserUpdateRequest
from app.schemas.moderations.user_update_request import UserUpdateRequestInfo


def test_response_preserves_explicitly_cleared_fields() -> None:
    request = UserUpdateRequest(
        id=1,
        user_id=2,
        request_at=datetime.now(UTC),
        moderation_status=ModerationStatusEnum.pending,
        avatar_uri=None,
        description="",
        grade=None,
        update_fields=["avatar_uri", "description", "grade"],
    )
    payload = UserUpdateRequestInfo.model_validate(request).model_dump(mode="json")
    assert payload.get("update_fields") == ["avatar_uri", "description", "grade"]
    assert payload["avatar_uri"] is None
    assert payload["description"] == ""
    assert payload["grade"] is None
