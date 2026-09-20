from typing import Any, Final

from app.schemas.generic import ErrorResponseModel

ALTCHA_VERIFICATION_FAILED_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    400: {
        "model": ErrorResponseModel,
        "description": "ALTCHA verification failed",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.altcha.verification_failed",
                    "error_code": "ALTCHA_VERIFICATION_FAILED",
                },
            },
        },
    },
}

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

RESOURCE_NOT_FOUND_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    404: {
        "model": ErrorResponseModel,
        "description": "Resource Not Found",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.resource.not_found",
                    "error_code": "RESOURCE_NOT_FOUND",
                    "detail": {
                        "resource": "requested_resource",
                    },
                },
            },
        },
    },
}

DUPLICATE_REQUEST_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    409: {
        "model": ErrorResponseModel,
        "description": "Conflict - A pending request already exists.",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.moderation.duplicate_pending_request",
                    "error_code": "DUPLICATE_PENDING_REQUEST",
                },
            },
        },
    },
}


VERIFICATION_CODE_INVALID_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    400: {
        "model": ErrorResponseModel,
        "description": (
            "The code is wrong, expired, already used, or out of attempts — "
            "deliberately not distinguished."
        ),
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.verification.code_invalid",
                    "error_code": "VERIFICATION_CODE_INVALID",
                },
            },
        },
    },
    409: {
        "model": ErrorResponseModel,
        "description": "The address or number already belongs to another account",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.verification.target_taken",
                    "error_code": "VERIFICATION_TARGET_TAKEN",
                },
            },
        },
    },
}

# Reset confirm can only fail on the code itself — there is no address being
# claimed here, so the 409 the binding flow can return does not apply.
PASSWORD_RESET_CODE_INVALID_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    400: VERIFICATION_CODE_INVALID_RESPONSE[400],
}

CONTACT_VERIFICATION_SEND_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    400: {
        "model": ErrorResponseModel,
        "description": "The address or number is not one this deployment can reach",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.verification.target_invalid",
                    "error_code": "VERIFICATION_TARGET_INVALID",
                },
            },
        },
    },
    409: VERIFICATION_CODE_INVALID_RESPONSE[409],
    429: {
        "model": ErrorResponseModel,
        "description": "A send budget was hit; retry after the given delay",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.verification.send_throttled",
                    "error_code": "VERIFICATION_SEND_THROTTLED",
                    "details": {"retry_after": 60},
                },
            },
        },
    },
    503: {
        "model": ErrorResponseModel,
        "description": "The email or SMS provider could not be reached",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.verification.channel_unavailable",
                    "error_code": "VERIFICATION_CHANNEL_UNAVAILABLE",
                },
            },
        },
    },
}


# Every route under /auth/2fa that re-checks the password can answer 401 with
# this, in addition to the 401 an absent session already produces.
PASSWORD_REQUIRED_RESPONSE: Final[dict[int | str, dict[str, Any]]] = {
    401: {
        "description": "Session missing or password incorrect",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.auth.incorrect_user_passwd",
                    "error_code": "INCORRECT_USER_PASSWD",
                    "details": {},
                },
            },
        },
    },
}

TWO_FACTOR_LOGIN_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    401: {
        "description": "Challenge ticket expired or second factor wrong",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.auth.two_factor_code_invalid",
                    "error_code": "TWO_FACTOR_CODE_INVALID",
                    "details": {},
                },
            },
        },
    },
    400: {
        "description": "That method is not armed on this account",
        "content": {
            "application/json": {
                "example": {
                    "message_key": "error.auth.two_factor_method_unavailable",
                    "error_code": "TWO_FACTOR_METHOD_UNAVAILABLE",
                    "details": {"method": "sms"},
                },
            },
        },
    },
}
