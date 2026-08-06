from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import ReadinessError
from app.schemas.health import HealthResponse


class ReadinessService(Protocol):
    async def ensure_ready(self) -> None: ...

    def get_status(self) -> HealthResponse: ...


class DatabaseReadinessService:
    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession], version: str) -> None:
        self._session_factory = session_factory
        self._version = version

    async def ensure_ready(self) -> None:
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            raise ReadinessError from exc

    def get_status(self) -> HealthResponse:
        return HealthResponse(version=self._version)
