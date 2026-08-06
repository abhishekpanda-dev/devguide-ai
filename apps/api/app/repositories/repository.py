from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Repository


class RepositoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, repository: Repository) -> Repository:
        self._session.add(repository)
        await self._session.flush()
        await self._session.refresh(repository)
        return repository

    async def get_by_id(self, repository_id: UUID) -> Repository | None:
        statement = select(Repository).where(Repository.id == repository_id)
        result: Repository | None = await self._session.scalar(statement)
        return result

    async def get_by_normalized_url(self, normalized_url: str) -> Repository | None:
        statement = select(Repository).where(Repository.normalized_url == normalized_url)
        result: Repository | None = await self._session.scalar(statement)
        return result

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[Repository]:
        statement = (
            select(Repository)
            .order_by(Repository.created_at.desc(), Repository.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.scalars(statement)).all())
