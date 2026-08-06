from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnalysisNotFoundError,
    ApplicationValidationError,
    PersistenceError,
    ResourceNotFoundError,
)
from app.models import AnalysisJob, AnalysisJobStatus
from app.repositories import AnalysisJobRepository
from app.schemas import AnalysisJobCreate


class AnalysisJobService:
    def __init__(
        self,
        session: AsyncSession,
        repository: AnalysisJobRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or AnalysisJobRepository(session)

    async def create(self, data: AnalysisJobCreate) -> AnalysisJob:
        model = AnalysisJob(
            repository_id=data.repository_id,
            status=data.status,
            current_stage=data.current_stage,
            progress_percent=data.progress_percent,
            pipeline_version=data.pipeline_version,
        )
        try:
            result = await self._repository.create(model)
            await self._session.commit()
            return result
        except IntegrityError as exc:
            await self._session.rollback()
            raise ApplicationValidationError("The repository reference is invalid.") from exc
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc

    async def get_required(self, analysis_job_id: UUID) -> AnalysisJob:
        try:
            analysis_job = await self._repository.get_by_id(analysis_job_id)
        except SQLAlchemyError as exc:
            raise PersistenceError from exc
        if analysis_job is None:
            raise AnalysisNotFoundError
        return analysis_job

    async def list_for_repository(
        self, repository_id: UUID, *, limit: int, offset: int
    ) -> list[AnalysisJob]:
        try:
            return await self._repository.list_for_repository(
                repository_id, limit=limit, offset=offset
            )
        except SQLAlchemyError as exc:
            raise PersistenceError from exc

    async def update_status(self, analysis_job_id: UUID, status: AnalysisJobStatus) -> AnalysisJob:
        try:
            result = await self._repository.update_status(analysis_job_id, status)
            if result is None:
                await self._session.rollback()
                raise ResourceNotFoundError("Analysis job")
            await self._session.commit()
            return result
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc

    async def update_progress(self, analysis_job_id: UUID, progress_percent: int) -> AnalysisJob:
        if not 0 <= progress_percent <= 100:
            raise ApplicationValidationError("Progress must be between 0 and 100.")
        try:
            result = await self._repository.update_progress(analysis_job_id, progress_percent)
            if result is None:
                await self._session.rollback()
                raise ResourceNotFoundError("Analysis job")
            await self._session.commit()
            return result
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc
