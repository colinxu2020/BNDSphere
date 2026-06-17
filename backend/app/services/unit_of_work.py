from types import TracebackType
from typing import Literal, Self

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    _DEPTH_KEY = "unit_of_work_depth"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._root = False

    async def __aenter__(self) -> Self:
        """Enter a transaction boundary."""
        depth = int(self.db.info.get(self._DEPTH_KEY, 0))
        self._root = depth == 0
        self.db.info[self._DEPTH_KEY] = depth + 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> Literal[False]:
        """Commit or roll back the outermost transaction boundary."""
        depth = int(self.db.info.get(self._DEPTH_KEY, 1)) - 1
        if depth > 0:
            self.db.info[self._DEPTH_KEY] = depth
            return False

        self.db.info.pop(self._DEPTH_KEY, None)
        if not self._root or not self.db.in_transaction():
            return False

        if exc_type is None:
            await self.db.commit()
        else:
            await self.db.rollback()
        return False
