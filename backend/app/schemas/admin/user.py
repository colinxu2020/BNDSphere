from pydantic import Field

from app.models.user import RoleEnum
from app.schemas.user import UserUpdate


class AdminUserUpdate(UserUpdate):
    role: RoleEnum | None = Field(None)
