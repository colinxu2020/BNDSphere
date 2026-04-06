class BusinessBaseError(Exception):
    def __init__(self, message: str, status: int) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


class DuplicateUsernameError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateClubNameError(Exception):
    pass


class ClubNotFoundError(BusinessBaseError):
    def __init__(self) -> None:
        super().__init__("Club not found", 404)


class ClubNotActiveError(BusinessBaseError):
    def __init__(self) -> None:
        super().__init__("Club is not active", 400)
