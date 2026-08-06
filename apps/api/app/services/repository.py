from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ApplicationValidationError,
    PersistenceError,
    ResourceConflictError,
)
from app.models import Repository
from app.repositories import RepositoryRepository
from app.schemas import RepositoryCreate


class RepositoryService:
    def __init__(
        self,
        session: AsyncSession,
        repository: RepositoryRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or RepositoryRepository(session)

    async def create(self, data: RepositoryCreate) -> Repository:
        if urlsplit(str(data.source_url)).hostname != "github.com":
            raise ApplicationValidationError("Only public GitHub repository URLs are supported.")
        if urlsplit(str(data.normalized_url)).hostname != "github.com":
            raise ApplicationValidationError("The normalized URL must use github.com.")

        model = Repository(
            source_type=data.source_type,
            source_url=str(data.source_url),
            normalized_url=str(data.normalized_url),
            owner=data.owner,
            name=data.name,
            default_branch=data.default_branch,
            latest_commit_sha=data.latest_commit_sha,
            status=data.status,
        )
        try:
            result = await self._repository.create(model)
            await self._session.commit()
            return result
        except IntegrityError as exc:
            await self._session.rollback()
            raise ResourceConflictError(
                "A repository with this normalized URL already exists."
            ) from exc
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc

    async def get_by_id(self, repository_id: UUID) -> Repository | None:
        try:
            return await self._repository.get_by_id(repository_id)
        except SQLAlchemyError as exc:
            raise PersistenceError from exc

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[Repository]:
        if not 1 <= limit <= 1000 or offset < 0:
            raise ApplicationValidationError("Pagination values are outside the supported range.")
        try:
            return await self._repository.list(limit=limit, offset=offset)
        except SQLAlchemyError as exc:
            raise PersistenceError from exc
