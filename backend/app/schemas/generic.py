from collections.abc import Collection
from typing import Any

from pydantic import BaseModel, Field

from app.services.errors import BadRequestError


class IdMixin(BaseModel):
    id: int


class ErrorResponseModel(BaseModel):
    message_key: str = Field(..., description="i18n translate key")
    error_code: str = Field(..., description="error code")
    details: dict[str, Any] = Field(default_factory=dict, description="extra context")


def ensure_non_nullable_fields_present(
    model: BaseModel,
    fields: Collection[str],
) -> None:
    for field in fields:
        if field in model.model_fields_set and getattr(model, field) is None:
            raise BadRequestError(
                "error.update_request.non_nullable_field_null",
                "NON_NULLABLE_FIELD_NULL",
                {"field": field},
            )
