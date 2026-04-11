from fastapi import APIRouter

from app.api.dependencies import UserServiceDep
from app.schemas.admin.user import AdminUserUpdate
from app.schemas.user import UserInfo
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["users"])


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    obj_in: AdminUserUpdate,
    user_service: UserServiceDep,
) -> UserInfo:
    user = await user_service.get(user_id)
    if user is None:
        raise ResourceNotFoundError(
            message_key="error.user.not_found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id},
        ) from None
    return UserInfo.model_validate(await user_service.update(user, obj_in))
