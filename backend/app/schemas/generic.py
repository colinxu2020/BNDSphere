from typing import Any

from pydantic import BaseModel, Field


class IdMixin(BaseModel):
    id: int


class ErrorResponseModel(BaseModel):
    message_key: str = Field(..., description="i18n translate key")
    error_code: str = Field(..., description="error code")
    details: dict[str, Any] = Field(default_factory=dict, description="extra context")
