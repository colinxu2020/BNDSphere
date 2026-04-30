from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models.moderations.moderation_common import ModerateStatusEnum
from app.schemas.generic import IdMixin
from app.services.errors import RequestIsNullError


class UserUpdateRequestCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str | None = Field(None)
    avatar_uri: HttpUrl | None = Field(None)
    description: str | None = Field(None)

    @model_validator(mode="after")
    def validate_not_null(self) -> UserUpdateRequestCreate:
        if (
            self.username is None
            and self.avatar_uri is None
            and self.description is None
        ):
            raise RequestIsNullError(
                "user.update_request.is_null",
                "USER_UPDATE_REQUEST_IS_NULL",
            )
        return self


class UserUpdateRequestInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(...)
    username: str | None = Field(None)
    avatar_uri: HttpUrl | None = Field(None)
    description: str | None = Field(None)

    moderate_status: ModerateStatusEnum = Field(...)
