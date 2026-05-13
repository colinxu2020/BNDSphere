from fastapi import APIRouter

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import UserServiceDep
from app.schemas.user import AdminUserUpdate, UserInfo
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["users"])


@router.patch(
    "/{user_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def admin_update_user(
    user_id: int,
    obj_in: AdminUserUpdate,
    user_service: UserServiceDep,
) -> UserInfo:
    """Update the information of a user."""
    user = await user_service.get(user_id)
    if user is None:
        raise ResourceNotFoundError(
            message_key="error.user.not_found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id},
        ) from None
    return UserInfo.model_validate(await user_service.update(user, obj_in))
