from typing import Any, Final

from app.schemas.generic import ErrorResponseModel

TOKEN_INVALID_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    401: {
        "model": ErrorResponseModel,
        "description": "Unauthorized or Token invalid",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.auth.token_invalid",
                    "error_code": "AUTH_TOKEN_INVALID",
                },
            },
        },
    },
}

PERMISSION_DENIED_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    403: {
        "model": ErrorResponseModel,
        "description": "Permission Denied",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.role.not_allowed",
                    "error_code": "ROLE_NOT_ALLOWED",
                },
            },
        },
    },
}
