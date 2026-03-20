from typing import Final

TOKEN_INVALID_RESPONSE: Final[dict] = {
    401: {
        "description": "Unauthorized",
        "content": {"application/json": {"example": {"detail": "Token is invalid or expired"}}}
    }
}