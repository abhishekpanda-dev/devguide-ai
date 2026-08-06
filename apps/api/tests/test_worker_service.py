from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import RepositoryCloneFailedError
from app.db.base import Base
from app.models import AnalysisJob, AnalysisJobStatus, AnalysisStageStatus, Repository
from app.repositories import AnalysisJobRepository, AnalysisStageRepository, RepositoryRepository
from app.schemas import RepositoryIngestionResult
from app.services.worker import AnalysisWorkerService


class FakeIngestion:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    async def ingest(
        self, repository: Repository, analysis_job: AnalysisJob
    ) -> RepositoryIngestionResult:
        self.calls += 1
        if self.fail:
            raise RepositoryCloneFailedError
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
    assert refreshed.progress_percent == 20
    assert result.progress_percent == 20


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
    assert result.attempt == 2


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
