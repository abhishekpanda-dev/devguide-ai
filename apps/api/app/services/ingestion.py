import re
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    InvalidRepositorySourceError,
    PersistenceError,
    RepositoryCloneFailedError,
)
from app.ingestion import GitCommandRunner, GitRunner, RepositoryScanner, RepositoryWorkspace
from app.models import AnalysisJob, Repository, RepositorySourceType
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.schemas import RepositoryIngestionResult
from app.services.repository_url import normalize_repository_url

_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_INGESTION_STAGE = "repository_ingestion"
_INGESTION_PROGRESS = 20

WorkspaceFactory = Callable[[Path], RepositoryWorkspace]


class RepositoryIngestionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repositories: RepositoryRepository,
        analysis_jobs: AnalysisJobRepository,
        settings: Settings,
        git_runner: GitRunner | None = None,
        workspace_factory: WorkspaceFactory = RepositoryWorkspace,
    ) -> None:
        self._session = session
        self._repositories = repositories
        self._analysis_jobs = analysis_jobs
        self._settings = settings
        self._git_runner = git_runner or GitCommandRunner(
            executable=settings.git_executable,
            timeout_seconds=settings.clone_timeout_seconds,
            clone_depth=settings.clone_depth,
        )
        self._workspace_factory = workspace_factory
        self._scanner = RepositoryScanner(
            maximum_file_count=settings.maximum_repository_file_count,
            maximum_repository_size_bytes=settings.maximum_repository_size_mb * 1024 * 1024,
            maximum_individual_file_size_bytes=(
                settings.maximum_individual_file_size_mb * 1024 * 1024
            ),
        )

    async def ingest(
        self, repository: Repository, analysis_job: AnalysisJob
    ) -> RepositoryIngestionResult:
        try:
            with self.create_workspace() as workspace:
                return await self.ingest_in_workspace(repository, analysis_job, workspace)
        except AppError:
            await self._session.rollback()
            raise
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc

    def create_workspace(self) -> RepositoryWorkspace:
        return self._workspace_factory(self._settings.temporary_workspace_root)

    async def ingest_in_workspace(
        self,
        repository: Repository,
        analysis_job: AnalysisJob,
        workspace: RepositoryWorkspace,
    ) -> RepositoryIngestionResult:
        normalized_url = self._validated_source(repository, analysis_job)
        try:
            await self._git_runner.clone(
                normalized_url, workspace.repository_path, workspace.metadata_path
            )
            commit_sha = (
                await self._git_runner.resolve_head(
                    workspace.repository_path, workspace.metadata_path
                )
            ).lower()
            if not _COMMIT_SHA.fullmatch(commit_sha):
                raise RepositoryCloneFailedError
            default_branch = await self._git_runner.discover_default_branch(
                workspace.repository_path, workspace.metadata_path
            )
            scan = self._scanner.scan(workspace.repository_path)
            updated_repository = await self._repositories.update_clone_metadata(
                repository.id, commit_sha=commit_sha, default_branch=default_branch
            )
            updated_analysis = await self._analysis_jobs.update_ingestion_state(
                analysis_job.id,
                current_stage=_INGESTION_STAGE,
                progress_percent=_INGESTION_PROGRESS,
            )
            if updated_repository is None or updated_analysis is None:
                raise PersistenceError
            await self._session.commit()
            limitations = list(scan.limitations)
            if default_branch is None:
                limitations.append("The default branch could not be determined safely.")
            return RepositoryIngestionResult(
                repository_id=repository.id,
                analysis_job_id=analysis_job.id,
                commit_sha=commit_sha,
                default_branch=default_branch,
                scanned_file_count=scan.file_count,
                scanned_size_bytes=scan.size_bytes,
                skipped_directory_count=scan.skipped_directory_count,
                completed_stage=_INGESTION_STAGE,
                limitations=limitations,
            )
        except AppError:
            await self._session.rollback()
            raise
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise PersistenceError from exc

    @staticmethod
    def _validated_source(repository: Repository, analysis_job: AnalysisJob) -> str:
        if (
            repository.source_type is not RepositorySourceType.GITHUB_PUBLIC
            or analysis_job.repository_id != repository.id
        ):
            raise InvalidRepositorySourceError
        try:
            normalized = normalize_repository_url(repository.normalized_url)
        except AppError as exc:
            raise InvalidRepositorySourceError from exc
        if normalized.normalized_url != repository.normalized_url:
            raise InvalidRepositorySourceError
        return normalized.normalized_url
