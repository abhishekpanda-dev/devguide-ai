import io
import json
import logging
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import gettempdir
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import RepositoryCloneFailedError
from app.core.logging import JsonFormatter
from app.db.base import Base
from app.ingestion import RepositoryWorkspace
from app.models import (
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisStage,
    AnalysisStageStatus,
    Repository,
)
from app.parser import RepositoryParser, RepositoryParseResult
from app.repositories import (
    AnalysisJobRepository,
    AnalysisStageRepository,
    ParsedRepository,
    RepositoryRepository,
)
from app.schemas import AnalysisJobRead, RepositoryIngestionResult, RepositoryRead
from app.services.worker import AnalysisWorkerService, WorkerResult


class FakeIngestion:
    def __init__(self, *, fail: bool = False, workspace_root: Path | None = None) -> None:
        self.calls = 0
        self.fail = fail
        self.workspace_root = workspace_root or Path(gettempdir()) / "devguide-worker-tests"
        self.workspace_path: Path | None = None

    def create_workspace(self) -> RepositoryWorkspace:
        return RepositoryWorkspace(self.workspace_root)

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


@pytest.fixture
async def expiring_worker_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=True)
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
    def __init__(self) -> None:
        super().__init__()
        self.repository_root: Path | None = None
        self.existed_during_parse = False

    def parse(self, repository_root: Path) -> RepositoryParseResult:
        self.repository_root = repository_root
        self.existed_during_parse = repository_root.is_dir()
        raise ValueError("forced parser failure")


class InspectingParser(RepositoryParser):
    def __init__(self) -> None:
        super().__init__()
        self.repository_root: Path | None = None
        self.existed_during_parse = False

    def parse(self, repository_root: Path) -> RepositoryParseResult:
        self.repository_root = repository_root
        self.existed_during_parse = repository_root.is_dir()
        return super().parse(repository_root)


class FailTrackingWorker(AnalysisWorkerService):
    fail_calls = 0

    async def _fail(self, job: AnalysisJob, stage: AnalysisStage, message: str) -> WorkerResult:
        self.fail_calls += 1
        return await super()._fail(job, stage, message)


async def test_successful_finalization_with_commit_expiration(
    expiring_worker_session: AsyncSession,
) -> None:
    repository = await RepositoryRepository(expiring_worker_session).create(
        Repository(
            source_url="https://github.com/acme/expiring-project",
            normalized_url="https://github.com/acme/expiring-project",
            owner="acme",
            name="expiring-project",
        )
    )
    job = await AnalysisJobRepository(expiring_worker_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    job_id = job.id
    await expiring_worker_session.commit()
    ingestion = FakeIngestion()
    worker = FailTrackingWorker(session=expiring_worker_session, ingestion=ingestion)

    result = await worker.process(job_id)

    stored = ParsedRepository(expiring_worker_session)
    parsing = await AnalysisStageRepository(expiring_worker_session).get_by_name(
        job_id, "repository_parsing"
    )
    refreshed = await AnalysisJobRepository(expiring_worker_session).get_by_id(job_id)
    assert len(await stored.list_files(job_id)) == 1
    assert len(await stored.list_chunks(job_id)) == 1
    assert parsing is not None
    assert parsing.status is AnalysisStageStatus.COMPLETED
    assert parsing.progress_percent == 100
    assert refreshed is not None
    assert refreshed.status is AnalysisJobStatus.RUNNING
    assert refreshed.progress_percent == 40
    assert result == WorkerResult(
        analysis_job_id=job_id,
        stage_name="repository_parsing",
        stage_status=AnalysisStageStatus.COMPLETED,
        analysis_status=AnalysisJobStatus.RUNNING,
        attempt=1,
        progress_percent=40,
    )
    assert worker.fail_calls == 0
    assert ingestion.workspace_path is not None and not ingestion.workspace_path.exists()


async def test_parser_receives_live_workspace_then_success_cleans_and_persists(
    worker_session: AsyncSession,
) -> None:
    _repository, job = await queued_job(worker_session)
    ingestion = FakeIngestion()
    parser = InspectingParser()

    result = await AnalysisWorkerService(
        session=worker_session, ingestion=ingestion, parser=parser
    ).process(job.id)

    stored = ParsedRepository(worker_session)
    assert parser.existed_during_parse
    assert parser.repository_root is not None
    assert ingestion.workspace_path is not None
    assert parser.repository_root == ingestion.workspace_path / "repository"
    assert not parser.repository_root.parent.exists()
    assert len(await stored.list_files(job.id)) == 1
    assert len(await stored.list_chunks(job.id)) == 1
    assert result.stage_status is AnalysisStageStatus.COMPLETED


async def test_permanent_cleanup_failure_after_persistence_is_operational_limitation(
    worker_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repository, job = await queued_job(worker_session)
    ingestion = FakeIngestion(workspace_root=tmp_path / "workspaces")
    original_rmtree = shutil.rmtree
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    worker_logger = logging.getLogger("app.services.worker")
    monkeypatch.setattr(worker_logger, "handlers", [handler])
    monkeypatch.setattr(worker_logger, "propagate", False)
    monkeypatch.setattr(worker_logger, "level", logging.ERROR)
    monkeypatch.setattr(worker_logger, "disabled", False)
    cleanup_attempts = 0

    def permanently_locked(*_args: object, **_kwargs: object) -> None:
        nonlocal cleanup_attempts
        cleanup_attempts += 1
        raise PermissionError

    monkeypatch.setattr("app.ingestion.workspace.shutil.rmtree", permanently_locked)
    monkeypatch.setattr("app.ingestion.workspace.time.sleep", lambda _delay: None)

    result = await AnalysisWorkerService(session=worker_session, ingestion=ingestion).process(
        job.id
    )

    parsing = await AnalysisStageRepository(worker_session).get_by_name(
        job.id, "repository_parsing"
    )
    refreshed = await AnalysisJobRepository(worker_session).get_by_id(job.id)
    stored = ParsedRepository(worker_session)
    assert parsing is not None and parsing.status is AnalysisStageStatus.COMPLETED
    assert refreshed is not None and refreshed.status is AnalysisJobStatus.RUNNING
    assert refreshed.progress_percent == 40
    assert len(await stored.list_files(job.id)) == 1
    assert len(await stored.list_chunks(job.id)) == 1
    assert result.stage_status is AnalysisStageStatus.COMPLETED
    assert result.analysis_status is AnalysisJobStatus.RUNNING
    assert result.progress_percent == 40
    assert result.error_code is None
    assert result.limitations == ("workspace_cleanup_failed",)
    assert cleanup_attempts == 3
    assert ingestion.workspace_path is not None
    assert str(ingestion.workspace_path) not in result.limitations
    logged = json.loads(stream.getvalue())
    assert logged["message"] == "repository_workspace_cleanup_failed"
    assert logged["analysis_job_id"] == str(job.id)
    assert logged["stage_name"] == "repository_parsing"
    assert "RepositoryWorkspaceError: exception details redacted" in logged["exception"]
    assert str(ingestion.workspace_path) not in stream.getvalue()

    monkeypatch.setattr("app.ingestion.workspace.shutil.rmtree", original_rmtree)
    original_rmtree(ingestion.workspace_path)


async def test_parsing_failure_marks_parsing_stage_failed_and_cleans_workspace(
    worker_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repository, job = await queued_job(worker_session)
    ingestion = FakeIngestion()
    parser = FailingParser()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    worker_logger = logging.getLogger("app.services.worker")
    monkeypatch.setattr(worker_logger, "handlers", [handler])
    monkeypatch.setattr(worker_logger, "propagate", False)
    monkeypatch.setattr(worker_logger, "level", logging.ERROR)
    monkeypatch.setattr(worker_logger, "disabled", False)
    result = await AnalysisWorkerService(
        session=worker_session, ingestion=ingestion, parser=parser
    ).process(job.id)
    parsing = await AnalysisStageRepository(worker_session).get_by_name(
        job.id, "repository_parsing"
    )
    refreshed = await AnalysisJobRepository(worker_session).get_by_id(job.id)
    assert result.error_code == "analysis_stage_failed"
    assert result.stage_name == "repository_parsing"
    assert parsing is not None and parsing.status is AnalysisStageStatus.FAILED
    assert parsing.error_code == "analysis_stage_failed"
    assert parsing.error_message == "Repository parsing could not be completed."
    assert refreshed is not None and refreshed.status is AnalysisJobStatus.FAILED
    assert refreshed.error_code == "analysis_stage_failed"
    assert refreshed.error_message == "Repository parsing could not be completed."
    assert parser.existed_during_parse
    assert parser.repository_root is not None
    assert ingestion.workspace_path is not None and not ingestion.workspace_path.exists()
    logged = json.loads(stream.getvalue())
    assert logged["message"] == "analysis_worker_stage_failed"
    assert logged["analysis_job_id"] == str(job.id)
    assert logged["stage_name"] == "repository_parsing"
    assert logged["exception_type"] == "ValueError"
    assert logged["correlation_id"] == "unavailable"
    assert "Traceback (most recent call last)" in logged["exception"]
    assert "ValueError: exception details redacted" in logged["exception"]
    assert "forced parser failure" not in logged["exception"]
    assert str(ingestion.workspace_path) not in logged["exception"]


def test_public_api_schemas_do_not_expose_temporary_workspace_paths() -> None:
    forbidden = {"workspace", "workspace_path", "repository_path", "temporary_path"}
    assert forbidden.isdisjoint(RepositoryRead.model_fields)
    assert forbidden.isdisjoint(AnalysisJobRead.model_fields)
