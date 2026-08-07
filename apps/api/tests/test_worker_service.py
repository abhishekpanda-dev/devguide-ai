from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import gettempdir
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import RepositoryCloneFailedError
from app.db.base import Base
from app.ingestion import RepositoryWorkspace
from app.models import AnalysisJob, AnalysisJobStatus, AnalysisStageStatus, Repository
from app.parser import RepositoryParser, RepositoryParseResult
from app.repositories import (
    AnalysisJobRepository,
    AnalysisStageRepository,
    ParsedRepository,
    RepositoryRepository,
)
from app.schemas import RepositoryIngestionResult
from app.services.worker import AnalysisWorkerService


class FakeIngestion:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail
        self.workspace_path: Path | None = None

    def create_workspace(self) -> RepositoryWorkspace:
        return RepositoryWorkspace(Path(gettempdir()) / "devguide-worker-tests")

    async def ingest_in_workspace(
        self,
        repository: Repository,
        analysis_job: AnalysisJob,
        workspace: RepositoryWorkspace,
    ) -> RepositoryIngestionResult:
        self.calls += 1
        self.workspace_path = workspace.path
        if self.fail:
            raise RepositoryCloneFailedError
        (workspace.repository_path / "source.py").write_text("value = 1\n", encoding="utf-8")
        repository.latest_commit_sha = "a" * 40
        return RepositoryIngestionResult(
            repository_id=repository.id,
            analysis_job_id=analysis_job.id,
            commit_sha="a" * 40,
            default_branch="main",
            scanned_file_count=1,
            scanned_size_bytes=1,
            skipped_directory_count=0,
            completed_stage="repository_ingestion",
            limitations=[],
        )


@pytest.fixture
async def worker_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def queued_job(session: AsyncSession) -> tuple[Repository, AnalysisJob]:
    repository = await RepositoryRepository(session).create(
        Repository(
            source_url="https://github.com/acme/project",
            normalized_url="https://github.com/acme/project",
            owner="acme",
            name="project",
        )
    )
    job = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await session.commit()
    return repository, job


async def test_queued_job_runs_ingestion_stage_and_remains_running(
    worker_session: AsyncSession,
) -> None:
    _repository, job = await queued_job(worker_session)
    ingestion = FakeIngestion()
    result = await AnalysisWorkerService(session=worker_session, ingestion=ingestion).process(
        job.id
    )

    stage = (await AnalysisStageRepository(worker_session).list_for_analysis_job(job.id))[0]
    refreshed = await AnalysisJobRepository(worker_session).get_by_id(job.id)
    assert ingestion.calls == 1
    assert stage.status is AnalysisStageStatus.COMPLETED
    assert stage.attempt == 1
    assert stage.progress_percent == 100
    assert stage.heartbeat_at is not None
    assert stage.completed_at is not None
    assert refreshed is not None
    assert refreshed.status is AnalysisJobStatus.RUNNING
    assert refreshed.progress_percent == 40
    assert result.progress_percent == 40
    assert ingestion.workspace_path is not None and not ingestion.workspace_path.exists()


async def test_non_queued_job_is_not_claimed(worker_session: AsyncSession) -> None:
    _repository, job = await queued_job(worker_session)
    job.status = AnalysisJobStatus.CANCELLED
    await worker_session.commit()
    ingestion = FakeIngestion()

    result = await AnalysisWorkerService(session=worker_session, ingestion=ingestion).process(
        job.id
    )

    assert result.error_code == "analysis_job_not_claimable"
    assert ingestion.calls == 0


async def test_duplicate_delivery_does_not_rerun_completed_stage(
    worker_session: AsyncSession,
) -> None:
    _repository, job = await queued_job(worker_session)
    ingestion = FakeIngestion()
    worker = AnalysisWorkerService(session=worker_session, ingestion=ingestion)
    await worker.process(job.id)
    duplicate = await worker.process(job.id)

    assert ingestion.calls == 1
    assert duplicate.stage_status is AnalysisStageStatus.COMPLETED
    assert duplicate.limitations
    assert len(await ParsedRepository(worker_session).list_files(job.id)) == 1
    assert len(await ParsedRepository(worker_session).list_chunks(job.id)) == 1


async def test_stage_attempt_increments_when_pending_stage_exists(
    worker_session: AsyncSession,
) -> None:
    _repository, job = await queued_job(worker_session)
    stages = AnalysisStageRepository(worker_session)
    from app.models import AnalysisStage

    await stages.create(
        AnalysisStage(
            analysis_job_id=job.id,
            name="repository_ingestion",
            status=AnalysisStageStatus.PENDING,
            attempt=1,
        )
    )
    await worker_session.commit()

    result = await AnalysisWorkerService(session=worker_session, ingestion=FakeIngestion()).process(
        job.id
    )
    ingestion_stage = await stages.get_by_name(job.id, "repository_ingestion")
    assert ingestion_stage is not None
    assert ingestion_stage.attempt == 2
    assert result.stage_name == "repository_parsing"


async def test_ingestion_failure_marks_stage_and_analysis_failed(
    worker_session: AsyncSession,
) -> None:
    _repository, job = await queued_job(worker_session)
    result = await AnalysisWorkerService(
        session=worker_session, ingestion=FakeIngestion(fail=True)
    ).process(job.id)

    stage = (await AnalysisStageRepository(worker_session).list_for_analysis_job(job.id))[0]
    refreshed = await AnalysisJobRepository(worker_session).get_by_id(job.id)
    assert result.error_code == "analysis_stage_failed"
    assert stage.status is AnalysisStageStatus.FAILED
    assert stage.error_message == "Repository ingestion could not be completed."
    assert refreshed is not None
    assert refreshed.status is AnalysisJobStatus.FAILED
    assert refreshed.error_code == "analysis_stage_failed"
    assert refreshed.completed_at is not None


async def test_missing_job_returns_typed_noop(worker_session: AsyncSession) -> None:
    result = await AnalysisWorkerService(session=worker_session, ingestion=FakeIngestion()).process(
        UUID("00000000-0000-0000-0000-000000000001")
    )
    assert result.error_code == "analysis_job_not_found"


class FailingParser(RepositoryParser):
    def parse(self, repository_root: Path) -> RepositoryParseResult:
        raise ValueError("forced parser failure")


async def test_parsing_failure_marks_parsing_stage_failed_and_cleans_workspace(
    worker_session: AsyncSession,
) -> None:
    _repository, job = await queued_job(worker_session)
    ingestion = FakeIngestion()
    result = await AnalysisWorkerService(
        session=worker_session, ingestion=ingestion, parser=FailingParser()
    ).process(job.id)
    parsing = await AnalysisStageRepository(worker_session).get_by_name(
        job.id, "repository_parsing"
    )
    refreshed = await AnalysisJobRepository(worker_session).get_by_id(job.id)
    assert result.error_code == "analysis_stage_failed"
    assert parsing is not None and parsing.status is AnalysisStageStatus.FAILED
    assert refreshed is not None and refreshed.status is AnalysisJobStatus.FAILED
    assert ingestion.workspace_path is not None and not ingestion.workspace_path.exists()
