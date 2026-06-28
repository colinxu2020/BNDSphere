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
