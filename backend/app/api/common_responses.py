from typing import Any, Final

TOKEN_INVALID_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {"example": {"detail": "Token is invalid or expired"}},
        },
    },
}
PERMISSION_DENIED_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    403: {
        "description": "Permission Denied",
        "content": {
            "application/json": {"example": {"detail": "Permission Denied"}},
        },
    },
}
