from typing import Any


class BusinessError(Exception):
    def __init__(
        self,
        message_key: str,
        status_code: int,
        error_code: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message_key = message_key
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        self.headers = headers
        super().__init__(error_code)


class AuthenticationError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
    ) -> None:
        super().__init__(
            message_key,
            401,
            error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ResourceNotFoundError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_key, 404, error_code, details)


class StarLevelNotFoundError(ResourceNotFoundError):
    def __init__(self, star_level_id: int) -> None:
        super().__init__(
            "error.star_level.not_found",
            "STAR_LEVEL_NOT_FOUND",
            {"star_level_id": star_level_id},
        )


class BusinessPermissionError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_key, 403, error_code, details)


class StarLevelApplicationUpdateDeniedError(BusinessPermissionError):
    def __init__(self, star_level_id: int) -> None:
        super().__init__(
            "error.star_level.denied",
            "STAR_LEVEL_UPDATE_DENIED",
            {"star_level_id": star_level_id},
        )


class ClubNotFoundError(ResourceNotFoundError):
    def __init__(self, club_id: int) -> None:
        super().__init__(
            "error.club.not_found",
            "CLUB_NOT_FOUND",
            {"club_id": club_id},
        )


class GeneralActivityNotFoundError(ResourceNotFoundError):
    def __init__(self, activity_id: int) -> None:
        super().__init__(
            "error.general_activity.not_found",
            "GENERAL_ACTIVITY_NOT_FOUND",
            {"general_activity_id": activity_id},
        )


class AcademicTermNotFoundError(ResourceNotFoundError):
    def __init__(self, term_id: int) -> None:
        super().__init__(
            "error.academic_term.not_found",
            "ACADEMIC_TERM_NOT_FOUND",
            {"academic_term_id": term_id},
        )


class DuplicateResourceError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_key, 409, error_code, details)


class ResourceForbiddenError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_key, 403, error_code, details)


class DuplicateUsernameError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateClubNameError(Exception):
    pass


class ClubUpdateRequestNotFoundError(ResourceNotFoundError):
    def __init__(self, request_id: int) -> None:
        super().__init__(
            "error.club.update_request_not_found",
            "CLUB_UPDATE_REQUEST_NOT_FOUND",
            {"request_id": request_id},
        )
