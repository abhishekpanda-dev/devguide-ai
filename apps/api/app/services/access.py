from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AnalysisNotFoundError, RepositoryNotFoundError
from app.models import AnalysisJob, UserRepositoryAccess


class AccessControlService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def grant_repository(self, user_id: UUID, repository_id: UUID) -> None:
        existing = await self._session.get(
            UserRepositoryAccess, {"user_id": user_id, "repository_id": repository_id}
        )
        if existing is None:
            self._session.add(UserRepositoryAccess(user_id=user_id, repository_id=repository_id))
            await self._session.commit()

    async def ensure_repository(self, user_id: UUID, repository_id: UUID) -> None:
        access = await self._session.get(
            UserRepositoryAccess, {"user_id": user_id, "repository_id": repository_id}
        )
        if access is None:
            raise RepositoryNotFoundError

    async def ensure_analysis(self, user_id: UUID, analysis_id: UUID) -> None:
        statement = (
            select(AnalysisJob.id)
            .join(
                UserRepositoryAccess,
                UserRepositoryAccess.repository_id == AnalysisJob.repository_id,
            )
            .where(
                AnalysisJob.id == analysis_id,
                UserRepositoryAccess.user_id == user_id,
            )
        )
        if await self._session.scalar(statement) is None:
            raise AnalysisNotFoundError
