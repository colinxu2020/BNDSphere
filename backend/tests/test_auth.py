from typing import ClassVar

from httpx import AsyncClient


class TestAuthWorkflow:
    async def test_create_user(self, client: AsyncClient) -> None:
        payload = {
            "username": "test_user_1",
            "password": "ada8d837f6b62e24",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 201

    async def test_create_user_username_duplicate(self, client: AsyncClient) -> None:
        payload = {
            "username": "test_user_1",
            "password": "6748dfa41e25ffbf",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_shared_state_survives_rollback(self, client: AsyncClient) -> None:
        # Regression guard for the class-scoped transaction: the previous test's
        # duplicate-username 409 triggers a session rollback inside the request.
        # That rollback must only unwind to the savepoint, not the outer
        # transaction, so ``test_user_1`` created in ``test_create_user`` is
        # still present here — a fresh registration with the same username must
        # therefore still conflict (409), not succeed (201).
        payload = {
            "username": "test_user_1",
            "password": "3f1c9a7b2d4e6f80",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409


class TestSeededUsersSurviveRollback:
    """Regression guard for ``setup_class_users``.

    The fixture seeds ``seeded_user`` and commits (releases its savepoint)
    before yielding, so the seeded row joins the outer class transaction. The
    first test below triggers a duplicate-username 409 whose request-time
    rollback only unwinds its own savepoint, so the seeded user must still
    conflict in the second test. Before the fix, that rollback deleted the
    seeded row and the second registration returned 201.
    """

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "seeded_user", "password": "ada8d837f6b62e24"},
    ]

    async def test_first_request_triggers_rollback(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        payload = {"username": "seeded_user", "password": "6748dfa41e25ffbf"}
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_seeded_user_still_exists(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        payload = {"username": "seeded_user", "password": "3f1c9a7b2d4e6f80"}
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409
