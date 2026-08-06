from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AnalysisDispatchFailedError, AppError, PersistenceError
from app.models import AnalysisJob, AnalysisJobStatus, Repository, RepositoryStatus
from app.queue import AnalysisQueue
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.services.repository_url import NormalizedRepositoryUrl, normalize_repository_url


@dataclass(frozen=True, slots=True)
class RepositorySubmissionResult:
    repository: Repository
    analysis_job: AnalysisJob


class RepositorySubmissionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repositories: RepositoryRepository,
        analysis_jobs: AnalysisJobRepository,
        pipeline_version: str,
        queue: AnalysisQueue,
    ) -> None:
        self._session = session
        self._repositories = repositories
        self._analysis_jobs = analysis_jobs
        self._pipeline_version = pipeline_version
        self._queue = queue

    async def submit(self, source_url: str) -> RepositorySubmissionResult:
        normalized = normalize_repository_url(source_url)
        try:
            repository = await self._repositories.get_by_normalized_url(normalized.normalized_url)
            if repository is None:
                repository = await self._create_repository_with_race_recovery(normalized)

            analysis_job = await self._analysis_jobs.create(
                AnalysisJob(
                    repository_id=repository.id,
                    status=AnalysisJobStatus.QUEUED,
                    progress_percent=0,
                    pipeline_version=self._pipeline_version,
                )
            )
            await self._session.commit()
            try:
                await self._queue.enqueue_analysis(
                    analysis_job.id, deduplication_key=f"analysis:{analysis_job.id}"
                )
            except AppError as exc:
                await self._analysis_jobs.mark_dispatch_failed(analysis_job.id)
                await self._session.commit()
                raise AnalysisDispatchFailedError from exc
            return RepositorySubmissionResult(
                repository=repository,
                analysis_job=analysis_job,
            )
        except PersistenceError:
            await self._session.rollback()
            raise
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc

    async def _create_repository_with_race_recovery(
        self, normalized: NormalizedRepositoryUrl
    ) -> Repository:
        repository = Repository(
            source_url=normalized.source_url,
            normalized_url=normalized.normalized_url,
            owner=normalized.owner,
            name=normalized.name,
            status=RepositoryStatus.PENDING,
        )
        try:
            return await self._repositories.create(repository)
        except IntegrityError as exc:
            if not _is_normalized_url_conflict(exc):
                raise
            await self._session.rollback()
            existing = await self._repositories.get_by_normalized_url(normalized.normalized_url)
            if existing is None:
                raise PersistenceError from exc
            return existing


def _is_normalized_url_conflict(exc: IntegrityError) -> bool:
    details = str(exc.orig).lower()
    return "uq_repositories_normalized_url" in details or "repositories.normalized_url" in details
