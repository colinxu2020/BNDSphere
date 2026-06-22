from httpx import AsyncClient


class TestAuthWorkFlow:
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
