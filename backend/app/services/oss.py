import inspect
from collections.abc import AsyncIterator, Awaitable, Mapping
from contextlib import asynccontextmanager
from typing import Final, Protocol, cast

import aioboto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.core.settings import oss_settings as get_oss_settings

S3_NOT_FOUND_CODES: Final[frozenset[str]] = frozenset({"404", "NoSuchKey", "NotFound"})


class S3Client(Protocol):
    def generate_presigned_url(self, **kwargs: object) -> str | Awaitable[str]: ...

    async def head_object(self, **kwargs: object) -> Mapping[str, object]: ...


class ObjectStorageService:
    def __init__(self) -> None:
        self.settings = get_oss_settings()
        self._session = aioboto3.Session(
            aws_access_key_id=self.settings.oss_access_key_id,
            aws_secret_access_key=self.settings.oss_access_key,
            region_name="auto",
        )
        self._client_config = Config(signature_version="s3v4")

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[S3Client]:
        async with self._session.client(
            "s3",
            endpoint_url=self.settings.oss_endpoint_url,
            config=self._client_config,
        ) as client:
            yield cast("S3Client", client)

    async def generate_put_presigned_url(
        self,
        object_key: str,
        content_type: str,
        expires_seconds: int,
    ) -> str:
        params = {
            "Bucket": self.settings.oss_bucket,
            "Key": object_key,
            "ContentType": content_type,
        }

        async with self._client() as client:
            result = client.generate_presigned_url(
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=expires_seconds,
                HttpMethod="PUT",
            )
            if inspect.isawaitable(result):
                result = await result
            return result

    async def stat_object(self, object_key: str) -> int | None:
        async with self._client() as client:
            try:
                result = await client.head_object(
                    Bucket=self.settings.oss_bucket,
                    Key=object_key,
                )
            except ClientError as exc:
                if _is_not_found_error(exc):
                    return None
                raise

            content_length = result.get("ContentLength")
            if isinstance(content_length, int):
                return content_length
            return None


def _is_not_found_error(exc: object) -> bool:
    response = getattr(exc, "response", None)
    if not isinstance(response, Mapping):
        return False

    error = response.get("Error", {})
    if not isinstance(error, Mapping):
        return False

    code = error.get("Code")
    if not isinstance(code, str):
        return False
    return code in S3_NOT_FOUND_CODES
