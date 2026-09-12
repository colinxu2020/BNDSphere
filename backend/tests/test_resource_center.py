from collections.abc import Iterator
from typing import ClassVar

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.user import RoleEnum
from app.services.oss import ObjectStorageService
from app.services.upload_policy import RESOURCE_FILE_MAX_SIZE


class FakeObjectStorageService:
    def __init__(self) -> None:
        self.object_sizes: dict[str, int] = {}
        self.deleted_keys: list[str] = []

    async def generate_put_presigned_url(
        self,
        object_key: str,
        _content_type: str,
        _expires_seconds: int,
    ) -> str:
        return f"https://uploads.example.test/{object_key}"

    async def stat_object(self, object_key: str) -> int | None:
        return self.object_sizes.get(object_key)

    async def generate_get_presigned_url(
        self,
        object_key: str,
        filename: str,
        _expires_seconds: int = 300,
    ) -> str:
        return f"https://downloads.example.test/{object_key}?filename={filename}"

    async def delete_object(self, object_key: str) -> None:
        self.deleted_keys.append(object_key)
        self.object_sizes.pop(object_key, None)


@pytest.mark.usefixtures("setup_class_users")
class TestResourceCenter:
    USER_SPECS: ClassVar[list[dict[str, str | RoleEnum]]] = [
        {
            "username": "resource_regular_user",
            "password": "ce0318b7c953d6ac",
            "role": RoleEnum.user,
        },
        {
            "username": "resource_federation_staff",
            "password": "47735b107f251fea",
            "role": RoleEnum.federation_staff,
        },
    ]
    configured_users: ClassVar[dict[str, dict[str, object]]]
    storage = FakeObjectStorageService()

    @pytest.fixture(scope="class", autouse=True)
    def override_object_storage(self) -> Iterator[None]:
        app.dependency_overrides[ObjectStorageService] = lambda: self.storage
        yield
        app.dependency_overrides.pop(ObjectStorageService, None)

    async def test_public_listing_is_available_without_login(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get("/resources/")
        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_regular_user_cannot_start_resource_upload(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/uploads/initiate",
            headers=self.configured_users["resource_regular_user"]["headers"],
            json={
                "scene": "resource_file",
                "filename": "archive.7z",
                "content_type": "application/x-7z-compressed",
                "size": 128,
            },
        )
        assert response.status_code == 403

    async def test_resource_upload_rejects_files_over_50_mib(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/uploads/initiate",
            headers=self.configured_users["resource_federation_staff"]["headers"],
            json={
                "scene": "resource_file",
                "filename": "large.bin",
                "content_type": "application/octet-stream",
                "size": RESOURCE_FILE_MAX_SIZE + 1,
            },
        )
        assert response.status_code == 413

    async def test_staff_can_publish_any_file_type_and_anyone_can_download_it(
        self,
        client: AsyncClient,
    ) -> None:
        staff_headers = self.configured_users["resource_federation_staff"]["headers"]
        initiate_response = await client.post(
            "/uploads/initiate",
            headers=staff_headers,
            json={
                "scene": "resource_file",
                "filename": "社团资料.7z",
                "content_type": "application/x-7z-compressed",
                "size": 128,
            },
        )
        assert initiate_response.status_code == 201
        object_key = initiate_response.json()["object_key"]
        self.storage.object_sizes[object_key] = 128

        create_response = await client.post(
            "/resources/",
            headers=staff_headers,
            json={
                "filename": "社团资料.7z",
                "object_key": object_key,
                "content_type": "application/x-7z-compressed",
            },
        )
        assert create_response.status_code == 201
        resource = create_response.json()
        assert resource["filename"] == "社团资料.7z"
        assert resource["file_size"] == 128

        listing_response = await client.get("/resources/")
        assert listing_response.status_code == 200
        assert listing_response.json()["items"][0]["id"] == resource["id"]

        download_response = await client.get(
            f"/resources/{resource['id']}/download",
            follow_redirects=False,
        )
        assert download_response.status_code == 307
        assert download_response.headers["location"].startswith(
            "https://downloads.example.test/",
        )

        denied_delete_response = await client.delete(
            f"/resources/{resource['id']}",
            headers=self.configured_users["resource_regular_user"]["headers"],
        )
        assert denied_delete_response.status_code == 403

        delete_response = await client.delete(
            f"/resources/{resource['id']}",
            headers=staff_headers,
        )
        assert delete_response.status_code == 200
        assert object_key in self.storage.deleted_keys

        missing_response = await client.get(f"/resources/{resource['id']}/download")
        assert missing_response.status_code == 404
