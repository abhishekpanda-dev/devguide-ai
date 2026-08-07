from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import RepositoryWorkspaceError
from app.findings import DeterministicFindingsAnalyzer
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
from app.services.finding import CodeFindingPersistenceService
from app.services.parser_persistence import ParserPersistenceService
from app.services.structure import RepositoryStructurePersistenceService
from app.structure import RepositoryStructureExtractor

INGESTION_STAGE = "repository_ingestion"
PARSING_STAGE = "repository_parsing"
FINDINGS_STAGE = "code_findings"
INTELLIGENCE_STAGE = "repository_intelligence"
READY_STAGE = "ready"


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
        findings_analyzer: DeterministicFindingsAnalyzer | None = None,
        findings_persistence: CodeFindingPersistenceService | None = None,
        structure_extractor: RepositoryStructureExtractor | None = None,
        structure_persistence: RepositoryStructurePersistenceService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._jobs = AnalysisJobRepository(session)
        self._stages = AnalysisStageRepository(session)
        self._repositories = RepositoryRepository(session)
        self._ingestion = ingestion
        self._parser = parser or RepositoryParser()
        self._persistence = persistence or ParserPersistenceService(session)
        configured = settings or Settings()
        self._findings_analyzer = findings_analyzer or DeterministicFindingsAnalyzer(
            large_file_line_threshold=configured.findings_large_file_line_threshold,
            maximum_findings=configured.maximum_findings_per_analysis,
        )
        self._findings_persistence = findings_persistence or CodeFindingPersistenceService(session)
        self._structure_extractor = structure_extractor or RepositoryStructureExtractor(
            maximum_edges=configured.maximum_dependency_edges_per_analysis
        )
        self._structure_persistence = (
            structure_persistence or RepositoryStructurePersistenceService(session)
        )

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
        intelligence_stage = await self._stages.get_by_name(job.id, INTELLIGENCE_STAGE)
        if (
            intelligence_stage is not None
            and intelligence_stage.status is AnalysisStageStatus.COMPLETED
        ):
            return WorkerResult(
                job.id,
                INTELLIGENCE_STAGE,
                intelligence_stage.status,
                job.status,
                intelligence_stage.attempt,
                job.progress_percent,
                limitations=(
                    "Duplicate delivery was ignored because repository intelligence "
                    "already completed.",
                ),
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
        repository = await self._repositories.get_by_id(claimed.repository_id)
        if repository is None:
            return await self._fail(
                claimed,
                await self._start_stage(claimed, INGESTION_STAGE, 10),
                "Repository ingestion could not be completed.",
            )
        ingestion_stage = await self._start_stage(claimed, INGESTION_STAGE, 10)
        completed_result: WorkerResult | None = None
        try:
            with self._ingestion.create_workspace() as workspace:
                ingestion = await self._ingestion.ingest_in_workspace(
                    repository, claimed, workspace
                )
                self._complete_stage(ingestion_stage)
                claimed.progress_percent = 20
                await self._session.commit()
                parsing_stage = await self._start_stage(claimed, PARSING_STAGE, 30)
                parsed = self._parser.parse(workspace.repository_path)
                await self._persistence.persist(
                    repository_id=repository.id,
                    analysis_job_id=claimed.id,
                    commit_sha=ingestion.commit_sha,
                    result=parsed,
                )
                self._complete_stage(parsing_stage)
                findings_stage = await self._start_stage(claimed, FINDINGS_STAGE, 60)
                findings = self._findings_analyzer.analyze(parsed, commit_sha=ingestion.commit_sha)
                await self._findings_persistence.persist(claimed.id, findings)
                self._complete_stage(findings_stage)
                intelligence_stage = await self._start_stage(claimed, INTELLIGENCE_STAGE, 80)
                structure = self._structure_extractor.analyze(parsed)
                await self._structure_persistence.persist(claimed.id, structure)
                self._complete_stage(intelligence_stage)
                completed = await self._jobs.mark_completed(claimed.id, current_stage=READY_STAGE)
                if completed is None:
                    raise RuntimeError("Running analysis could not be marked completed.")
                await self._session.commit()
                completed_result = WorkerResult(
                    claimed.id,
                    INTELLIGENCE_STAGE,
                    intelligence_stage.status,
                    completed.status,
                    intelligence_stage.attempt,
                    completed.progress_percent,
                    limitations=tuple(
                        (
                            *parsed.statistics.limitations,
                            *findings.limitations,
                            *structure.limitations,
                        )
                    ),
                )
            assert completed_result is not None
            return completed_result
        except RepositoryWorkspaceError:
            if completed_result is not None:
                return WorkerResult(
                    completed_result.analysis_job_id,
                    completed_result.stage_name,
                    completed_result.stage_status,
                    completed_result.analysis_status,
                    completed_result.attempt,
                    completed_result.progress_percent,
                    limitations=(
                        *completed_result.limitations,
                        "The temporary repository workspace could not be fully cleaned up.",
                    ),
                )
            stage = (
                await self._stages.get_by_name(claimed.id, INTELLIGENCE_STAGE)
                or await self._stages.get_by_name(claimed.id, FINDINGS_STAGE)
                or await self._stages.get_by_name(claimed.id, PARSING_STAGE)
                or ingestion_stage
            )
            message = (
                "Repository intelligence could not be completed."
                if stage.name == INTELLIGENCE_STAGE
                else "Code findings could not be completed."
                if stage.name == FINDINGS_STAGE
                else (
                    "Repository parsing could not be completed."
                    if stage.name == PARSING_STAGE
                    else "Repository ingestion could not be completed."
                )
            )
            return await self._fail(claimed, stage, message)
        except Exception:
            stage = (
                await self._stages.get_by_name(claimed.id, INTELLIGENCE_STAGE)
                or await self._stages.get_by_name(claimed.id, FINDINGS_STAGE)
                or await self._stages.get_by_name(claimed.id, PARSING_STAGE)
                or ingestion_stage
            )
            message = (
                "Repository intelligence could not be completed."
                if stage.name == INTELLIGENCE_STAGE
                else "Code findings could not be completed."
                if stage.name == FINDINGS_STAGE
                else (
                    "Repository parsing could not be completed."
                    if stage.name == PARSING_STAGE
                    else "Repository ingestion could not be completed."
                )
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
        now = datetime.now(UTC)
        stage.status = AnalysisStageStatus.FAILED
        stage.error_code = "analysis_stage_failed"
        stage.error_message = message
        stage.heartbeat_at = now
        stage.completed_at = now
        await self._jobs.mark_failed(
            job.id, error_code="analysis_stage_failed", error_message=message
        )
        await self._session.commit()
        return WorkerResult(
            job.id,
            stage.name,
            stage.status,
            AnalysisJobStatus.FAILED,
            stage.attempt,
            job.progress_percent,
            "analysis_stage_failed",
        )
