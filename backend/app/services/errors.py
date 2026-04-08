class BusinessError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFoundError(BusinessError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 404)


class DuplicateResourceError(BusinessError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 409)


class DuplicateUsernameError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateClubNameError(Exception):
    pass


class ClubNotFoundError(BusinessError):
    def __init__(self) -> None:
        super().__init__("Club not found", 404)


class ClubNotActiveError(BusinessError):
    def __init__(self) -> None:
        super().__init__("Club is not active", 400)
