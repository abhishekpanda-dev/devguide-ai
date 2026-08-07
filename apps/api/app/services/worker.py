import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RepositoryWorkspaceError
from app.core.middleware import correlation_id_context
from app.ingestion import RepositoryWorkspace
from app.models import (
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisStage,
    AnalysisStageStatus,
    Repository,
)
from app.parser import RepositoryParser
from app.repositories import AnalysisJobRepository, AnalysisStageRepository, RepositoryRepository
from app.schemas import RepositoryIngestionResult
from app.services.parser_persistence import ParserPersistenceService

INGESTION_STAGE = "repository_ingestion"
PARSING_STAGE = "repository_parsing"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkerResult:
    analysis_job_id: UUID
    stage_name: str
    stage_status: AnalysisStageStatus
    analysis_status: AnalysisJobStatus
    attempt: int
    progress_percent: int
    error_code: str | None = None
    limitations: tuple[str, ...] = ()


class IngestionService(Protocol):
    def create_workspace(self) -> RepositoryWorkspace: ...
    async def ingest_in_workspace(
        self, repository: Repository, analysis_job: AnalysisJob, workspace: RepositoryWorkspace
    ) -> RepositoryIngestionResult: ...


class AnalysisWorkerService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        ingestion: IngestionService,
        parser: RepositoryParser | None = None,
        persistence: ParserPersistenceService | None = None,
    ) -> None:
        self._session = session
        self._jobs = AnalysisJobRepository(session)
        self._stages = AnalysisStageRepository(session)
        self._repositories = RepositoryRepository(session)
        self._ingestion = ingestion
        self._parser = parser or RepositoryParser()
        self._persistence = persistence or ParserPersistenceService(session)

    async def process(self, analysis_job_id: UUID) -> WorkerResult:
        job = await self._jobs.get_by_id(analysis_job_id)
        if job is None:
            return WorkerResult(
                analysis_job_id,
                INGESTION_STAGE,
                AnalysisStageStatus.PENDING,
                AnalysisJobStatus.QUEUED,
                0,
                0,
                "analysis_job_not_found",
            )
        parsing = await self._stages.get_by_name(job.id, PARSING_STAGE)
        if parsing is not None and parsing.status is AnalysisStageStatus.COMPLETED:
            return WorkerResult(
                job.id,
                PARSING_STAGE,
                parsing.status,
                job.status,
                parsing.attempt,
                job.progress_percent,
                limitations=("Duplicate delivery was ignored because parsing already completed.",),
            )
        claimed = await self._jobs.claim_queued(job.id)
        if claimed is None:
            return WorkerResult(
                job.id,
                INGESTION_STAGE,
                AnalysisStageStatus.PENDING,
                job.status,
                0,
                job.progress_percent,
                "analysis_job_not_claimable",
            )
        claimed_id = claimed.id
        repository = await self._repositories.get_by_id(claimed.repository_id)
        if repository is None:
            return await self._fail(
                claimed,
                await self._start_stage(claimed, INGESTION_STAGE, 10),
                "Repository ingestion could not be completed.",
            )
        repository_id = repository.id
        ingestion_stage = await self._start_stage(claimed, INGESTION_STAGE, 10)
        await self._session.refresh(claimed)
        await self._session.refresh(repository)
        await self._session.refresh(ingestion_stage)
        successful_result: WorkerResult | None = None
        try:
            with self._ingestion.create_workspace() as workspace:
                ingestion = await self._ingestion.ingest_in_workspace(
                    repository, claimed, workspace
                )
                self._complete_stage(ingestion_stage)
                claimed.progress_percent = 20
                await self._session.commit()
                await self._session.refresh(claimed)
                parsing_stage = await self._start_stage(claimed, PARSING_STAGE, 30)
                parsed = self._parser.parse(workspace.repository_path)
                await self._persistence.persist(
                    repository_id=repository_id,
                    analysis_job_id=claimed_id,
                    commit_sha=ingestion.commit_sha,
                    result=parsed,
                )
                await self._session.refresh(claimed)
                await self._session.refresh(parsing_stage)
                self._complete_stage(parsing_stage)
                claimed.status = AnalysisJobStatus.RUNNING
                claimed.current_stage = PARSING_STAGE
                claimed.progress_percent = 40

                analysis_job_id = claimed_id
                attempt = parsing_stage.attempt
                limitations = tuple(parsed.statistics.limitations)
                await self._session.commit()
                successful_result = WorkerResult(
                    analysis_job_id=analysis_job_id,
                    stage_name=PARSING_STAGE,
                    stage_status=AnalysisStageStatus.COMPLETED,
                    analysis_status=AnalysisJobStatus.RUNNING,
                    attempt=attempt,
                    progress_percent=40,
                    limitations=limitations,
                )
            assert successful_result is not None
            return successful_result
        except RepositoryWorkspaceError as exc:
            if successful_result is not None:
                logger.exception(
                    "repository_workspace_cleanup_failed",
                    exc_info=exc,
                    extra={
                        "analysis_job_id": str(claimed_id),
                        "correlation_id": correlation_id_context.get(),
                        "stage_name": PARSING_STAGE,
                    },
                )
                return WorkerResult(
                    analysis_job_id=successful_result.analysis_job_id,
                    stage_name=successful_result.stage_name,
                    stage_status=successful_result.stage_status,
                    analysis_status=successful_result.analysis_status,
                    attempt=successful_result.attempt,
                    progress_percent=successful_result.progress_percent,
                    limitations=(*successful_result.limitations, "workspace_cleanup_failed"),
                )
            return await self._handle_stage_failure(claimed, ingestion_stage, claimed_id, exc)
        except Exception as exc:
            return await self._handle_stage_failure(claimed, ingestion_stage, claimed_id, exc)

    async def _handle_stage_failure(
        self,
        claimed: AnalysisJob,
        ingestion_stage: AnalysisStage,
        claimed_id: UUID,
        exc: Exception,
    ) -> WorkerResult:
        stage = await self._stages.get_by_name(claimed_id, PARSING_STAGE) or ingestion_stage
        logger.exception(
            "analysis_worker_stage_failed",
            exc_info=exc,
            extra={
                "analysis_job_id": str(claimed_id),
                "correlation_id": correlation_id_context.get(),
                "stage_name": stage.name,
                "exception_type": type(exc).__name__,
            },
        )
        message = (
            "Repository parsing could not be completed."
            if stage.name == PARSING_STAGE
            else "Repository ingestion could not be completed."
        )
        return await self._fail(claimed, stage, message)

    async def _start_stage(self, job: AnalysisJob, name: str, progress: int) -> AnalysisStage:
        stage = await self._stages.get_by_name(job.id, name)
        if stage is None:
            stage = await self._stages.create(
                AnalysisStage(analysis_job_id=job.id, name=name, attempt=1)
            )
        else:
            stage.attempt += 1
        now = datetime.now(UTC)
        stage.status = AnalysisStageStatus.RUNNING
        stage.progress_percent = progress
        stage.started_at = now
        stage.heartbeat_at = now
        job.current_stage = name
        job.progress_percent = progress
        await self._session.commit()
        return stage

    @staticmethod
    def _complete_stage(stage: AnalysisStage) -> None:
        now = datetime.now(UTC)
        stage.status = AnalysisStageStatus.COMPLETED
        stage.progress_percent = 100
        stage.heartbeat_at = now
        stage.completed_at = now

    async def _fail(self, job: AnalysisJob, stage: AnalysisStage, message: str) -> WorkerResult:
        await self._session.refresh(job)
        await self._session.refresh(stage)
        analysis_job_id = job.id
        stage_name = stage.name
        attempt = stage.attempt
        progress_percent = job.progress_percent
        now = datetime.now(UTC)
        stage.status = AnalysisStageStatus.FAILED
        stage.error_code = "analysis_stage_failed"
        stage.error_message = message
        stage.heartbeat_at = now
        stage.completed_at = now
        await self._jobs.mark_failed(
            analysis_job_id, error_code="analysis_stage_failed", error_message=message
        )
        await self._session.commit()
        return WorkerResult(
            analysis_job_id,
            stage_name,
            AnalysisStageStatus.FAILED,
            AnalysisJobStatus.FAILED,
            attempt,
            progress_percent,
            "analysis_stage_failed",
        )
