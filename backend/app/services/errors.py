class BusinessError(Exception):
    def __init__(
        self,
        message_key: str,
        status_code: int,
        error_code: str,
        details: dict | None = None,
    ) -> None:
        self.message_key = message_key
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(error_code)


class ResourceNotFoundError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(message_key, 404, error_code, details)


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


class DuplicateResourceError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(message_key, 409, error_code, details)


class ResourceForbiddenError(BusinessError):
    def __init__(
        self,
        message_key: str,
        error_code: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(message_key, 403, error_code, details)


class DuplicateUsernameError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateClubNameError(Exception):
    pass
