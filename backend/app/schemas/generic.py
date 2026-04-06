from collections.abc import Sequence

from pydantic import BaseModel


class PageResponse[T](BaseModel):
    total: int
    items: Sequence[T]


class IdMixin(BaseModel):
    id: int
