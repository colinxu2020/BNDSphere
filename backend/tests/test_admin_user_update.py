from typing import cast

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import AdminUserUpdate
from app.services.errors import DuplicateResourceError
from app.services.user import UserService


class TransactionlessSession:
    def __init__(self) -> None:
        self.info: dict[str, object] = {}

    def in_transaction(self) -> bool:
        return False


class ConstraintDiagnostic:
    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


class UniqueViolationError(Exception):
    def __init__(self, constraint_name: str) -> None:
        super().__init__(constraint_name)
        self.diag = ConstraintDiagnostic(constraint_name)


class ConflictingUserRepository:
    def __init__(self, constraint_name: str) -> None:
        self.db = TransactionlessSession()
        self.constraint_name = constraint_name

    async def update(self, user: User, update: AdminUserUpdate) -> User:
        raise IntegrityError(
            "UPDATE users SET username = ...",
            {"username": update.username},
            UniqueViolationError(self.constraint_name),
        )


@pytest.mark.parametrize("username", ["", "   "])
def test_admin_update_rejects_a_blank_username(username: str) -> None:
    with pytest.raises(ValidationError):
        AdminUserUpdate(username=username)


async def test_admin_update_reports_a_username_constraint_collision() -> None:
    repository = ConflictingUserRepository("ix_users_username")
    service = UserService(cast("UserRepository", repository))
    user = User(id=4, username="old-name", hashed_password="unused")  # noqa: S106

    with pytest.raises(DuplicateResourceError) as exc_info:
        await service.update(user, AdminUserUpdate(username="already-taken"))

    assert exc_info.value.error_code == "DUPLICATE_USERNAME"
    assert exc_info.value.details == {"username": "already-taken"}


async def test_admin_update_reports_an_email_constraint_collision() -> None:
    repository = ConflictingUserRepository("uq_users_email")
    service = UserService(cast("UserRepository", repository))
    user = User(id=4, username="old-name", hashed_password="unused")  # noqa: S106

    with pytest.raises(DuplicateResourceError) as exc_info:
        await service.update(user, AdminUserUpdate(email="used@example.com"))

    assert exc_info.value.error_code == "DUPLICATE_EMAIL"
    assert exc_info.value.details == {"email": "used@example.com"}


async def test_admin_update_preserves_an_unrecognized_integrity_error() -> None:
    repository = ConflictingUserRepository("unexpected_constraint")
    service = UserService(cast("UserRepository", repository))
    user = User(id=4, username="old-name", hashed_password="unused")  # noqa: S106

    with pytest.raises(IntegrityError):
        await service.update(user, AdminUserUpdate(description="updated"))
