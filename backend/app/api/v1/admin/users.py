from fastapi import APIRouter

from app.api.dependencies import UserServiceDep
from app.models.user import User
from app.schemas.admin.user import AdminUserUpdate
from app.schemas.user import UserInfo
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["users"])


@router.patch(
    "/{user_id}",
    response_model=UserInfo,
)
async def update_user(
    user_id: int,
    obj_in: AdminUserUpdate,
    user_service: UserServiceDep,
) -> User:
    user = await user_service.get(user_id)
    if user is None:
        raise ResourceNotFoundError(
            message_key="error.user.not_found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id},
        ) from None
    return await user_service.update(user, obj_in)
