from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import (
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisStage,
    AnalysisStageStatus,
    Repository,
)
from app.repositories import AnalysisJobRepository, AnalysisStageRepository, RepositoryRepository
from app.schemas import RepositoryIngestionResult

INGESTION_STAGE = "repository_ingestion"


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
    async def ingest(
        self, repository: Repository, analysis_job: AnalysisJob
    ) -> RepositoryIngestionResult: ...


class AnalysisWorkerService:
    def __init__(self, *, session: AsyncSession, ingestion: IngestionService) -> None:
        self._session = session
        self._jobs = AnalysisJobRepository(session)
        self._stages = AnalysisStageRepository(session)
        self._repositories = RepositoryRepository(session)
        self._ingestion = ingestion

    async def process(self, analysis_job_id: UUID) -> WorkerResult:
        job = await self._jobs.get_by_id(analysis_job_id)
        if job is None:
            return self._noop(analysis_job_id, "analysis_job_not_found")

        stage = await self._stages.get_by_name(job.id, INGESTION_STAGE)
        if stage is not None and stage.status is AnalysisStageStatus.COMPLETED:
            return WorkerResult(
                job.id,
                INGESTION_STAGE,
                stage.status,
                job.status,
                stage.attempt,
                job.progress_percent,
                limitations=(
                    "Duplicate delivery was ignored because ingestion already completed.",
                ),
            )

        claimed = await self._jobs.claim_queued(job.id)
        if claimed is None:
            return WorkerResult(
                job.id,
                INGESTION_STAGE,
                stage.status if stage else AnalysisStageStatus.PENDING,
                job.status,
                stage.attempt if stage else 0,
                job.progress_percent,
                error_code="analysis_job_not_claimable",
                limitations=("Only queued analysis jobs can be claimed.",),
            )

        now = datetime.now(UTC)
        if stage is None:
            stage = await self._stages.create(
                AnalysisStage(analysis_job_id=job.id, name=INGESTION_STAGE, attempt=1)
            )
        else:
            stage.attempt += 1
        stage.status = AnalysisStageStatus.RUNNING
        stage.progress_percent = 10
        stage.started_at = now
        stage.heartbeat_at = now
        stage.completed_at = None
        stage.error_code = None
        stage.error_message = None
        claimed.current_stage = INGESTION_STAGE
        claimed.progress_percent = 10
        await self._session.commit()

        repository = await self._repositories.get_by_id(claimed.repository_id)
        if repository is None:
            return await self._fail(
                claimed.id,
                stage,
                "analysis_stage_failed",
                "Repository ingestion could not be completed.",
            )

        try:
            ingestion_result = await self._ingestion.ingest(repository, claimed)
            stage.status = AnalysisStageStatus.COMPLETED
            stage.progress_percent = 100
            stage.heartbeat_at = datetime.now(UTC)
            stage.completed_at = stage.heartbeat_at
            claimed.status = AnalysisJobStatus.RUNNING
            claimed.progress_percent = 20
            await self._session.commit()
            return WorkerResult(
                claimed.id,
                INGESTION_STAGE,
                stage.status,
                claimed.status,
                stage.attempt,
                claimed.progress_percent,
                limitations=tuple(ingestion_result.limitations),
            )
        except AppError:
            return await self._fail(
                claimed.id,
                stage,
                "analysis_stage_failed",
                "Repository ingestion could not be completed.",
            )
        except SQLAlchemyError:
            await self._session.rollback()
            return await self._fail(
                claimed.id,
                stage,
                "analysis_stage_failed",
                "Repository ingestion could not be completed.",
            )

    async def _fail(
        self, job_id: UUID, stage: AnalysisStage, code: str, message: str
    ) -> WorkerResult:
        now = datetime.now(UTC)
        stage.status = AnalysisStageStatus.FAILED
        stage.error_code = code
        stage.error_message = message
        stage.heartbeat_at = now
        stage.completed_at = now
        job = await self._jobs.mark_failed(job_id, error_code=code, error_message=message)
        await self._session.commit()
        return WorkerResult(
            job_id,
            INGESTION_STAGE,
            stage.status,
            AnalysisJobStatus.FAILED,
            stage.attempt,
            job.progress_percent if job else 10,
            error_code=code,
        )

    @staticmethod
    def _noop(job_id: UUID, code: str) -> WorkerResult:
        return WorkerResult(
            job_id,
            INGESTION_STAGE,
            AnalysisStageStatus.PENDING,
            AnalysisJobStatus.QUEUED,
            0,
            0,
            error_code=code,
            limitations=("The requested analysis job does not exist.",),
        )
