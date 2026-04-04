from typing import override

from pydantic import HttpUrl, TypeAdapter
from sqlalchemy import Dialect, Text, TypeDecorator

url_adapter: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


class HttpUrlType(TypeDecorator[HttpUrl]):
    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: HttpUrl | str | None,
        dialect: Dialect,
    ) -> str | None:
        if value is None:
            return None
        return str(value)

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> HttpUrl | None:
        if value is None:
            return None
        return url_adapter.validate_python(value)

    @override
    def process_literal_param(
        self,
        value: HttpUrl | str | None,
        dialect: Dialect,
    ) -> str | None:
        if value is None:
            return None
        return str(value)
