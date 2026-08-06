from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.exceptions import InvalidRepositorySourceError
from app.db.base import Base
from app.ingestion.git_runner import GitRunner
from app.models import AnalysisJob, AnalysisJobStatus, Repository, RepositorySourceType
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.services.ingestion import RepositoryIngestionService


class FakeGitRunner(GitRunner):
    def __init__(self) -> None:
        self.clone_path: Path | None = None

    async def clone(self, repository_url: str, destination: Path, metadata_path: Path) -> None:
        assert repository_url == "https://github.com/acme/project"
        self.clone_path = destination
        (destination / "source.py").write_bytes(b"print('data only')")
        git_directory = destination / ".git"
        git_directory.mkdir()
        (git_directory / "large-object").write_bytes(b"x" * 1024)
        excluded = destination / "node_modules"
        excluded.mkdir()
        (excluded / "package.js").write_bytes(b"x" * 1024)

    async def resolve_head(self, repository_path: Path, metadata_path: Path) -> str:
        return "a" * 40

    async def discover_default_branch(
        self, repository_path: Path, metadata_path: Path
    ) -> str | None:
        return "main"


@pytest.fixture
async def ingestion_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def persisted_records(session: AsyncSession) -> tuple[Repository, AnalysisJob]:
    repository = await RepositoryRepository(session).create(
        Repository(
            source_type=RepositorySourceType.GITHUB_PUBLIC,
            source_url="https://github.com/acme/project",
            normalized_url="https://github.com/acme/project",
            owner="acme",
            name="project",
        )
    )
    analysis_job = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await session.commit()
    return repository, analysis_job


async def test_ingestion_updates_metadata_progress_and_cleans_workspace(
    ingestion_session: AsyncSession, tmp_path: Path
) -> None:
    repository, analysis_job = await persisted_records(ingestion_session)
    git_runner = FakeGitRunner()
    settings = Settings(
        environment="test",
        temporary_workspace_root=tmp_path / "workspaces",
        maximum_repository_size_mb=1,
        maximum_individual_file_size_mb=1,
        maximum_repository_file_count=10,
    )
    service = RepositoryIngestionService(
        session=ingestion_session,
        repositories=RepositoryRepository(ingestion_session),
        analysis_jobs=AnalysisJobRepository(ingestion_session),
        settings=settings,
        git_runner=git_runner,
    )

    result = await service.ingest(repository, analysis_job)

    refreshed_repository = await RepositoryRepository(ingestion_session).get_by_id(repository.id)
    refreshed_analysis = await AnalysisJobRepository(ingestion_session).get_by_id(analysis_job.id)
    assert result.commit_sha == "a" * 40
    assert result.default_branch == "main"
    assert result.scanned_file_count == 1
    assert result.skipped_directory_count == 2
    assert refreshed_repository is not None
    assert refreshed_repository.latest_commit_sha == "a" * 40
    assert refreshed_repository.default_branch == "main"
    assert refreshed_analysis is not None
    assert refreshed_analysis.status is AnalysisJobStatus.RUNNING
    assert refreshed_analysis.current_stage == "repository_ingestion"
    assert refreshed_analysis.progress_percent == 20
    assert refreshed_analysis.completed_at is None
    assert git_runner.clone_path is not None and not git_runner.clone_path.parent.exists()


async def test_ingestion_rejects_mismatched_repository_source(
    ingestion_session: AsyncSession, tmp_path: Path
) -> None:
    repository, analysis_job = await persisted_records(ingestion_session)
    analysis_job.repository_id = uuid4()
    service = RepositoryIngestionService(
        session=ingestion_session,
        repositories=RepositoryRepository(ingestion_session),
        analysis_jobs=AnalysisJobRepository(ingestion_session),
        settings=Settings(environment="test", temporary_workspace_root=tmp_path / "workspaces"),
        git_runner=FakeGitRunner(),
    )
    with pytest.raises(InvalidRepositorySourceError):
        await service.ingest(repository, analysis_job)
