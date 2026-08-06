from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import PersistenceError
from app.db.base import Base
from app.models import AnalysisJob, AnalysisJobStatus, Repository
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.services.submission import RepositorySubmissionService


@pytest.fixture
async def submission_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def submission_service(
    session: AsyncSession, *, pipeline_version: str = "pipeline-v1"
) -> RepositorySubmissionService:
    return RepositorySubmissionService(
        session=session,
        repositories=RepositoryRepository(session),
        analysis_jobs=AnalysisJobRepository(session),
        pipeline_version=pipeline_version,
    )


async def test_submission_creates_repository_and_queued_analysis(
    submission_session: AsyncSession,
) -> None:
    result = await submission_service(submission_session, pipeline_version="configured-v2").submit(
        "https://github.com/acme/project.git"
    )

    assert result.repository.normalized_url == "https://github.com/acme/project"
    assert result.repository.owner == "acme"
    assert result.repository.name == "project"
    assert result.analysis_job.repository_id == result.repository.id
    assert result.analysis_job.status is AnalysisJobStatus.QUEUED
    assert result.analysis_job.progress_percent == 0
    assert result.analysis_job.pipeline_version == "configured-v2"


async def test_repeated_submission_reuses_repository_and_creates_new_analysis(
    submission_session: AsyncSession,
) -> None:
    service = submission_service(submission_session)
    first = await service.submit("https://github.com/acme/project")
    second = await service.submit("https://github.com/acme/project/")

    assert second.repository.id == first.repository.id
    assert second.analysis_job.id != first.analysis_job.id
    jobs = await AnalysisJobRepository(submission_session).list_for_repository(first.repository.id)
    assert len(jobs) == 2


class FailingAnalysisJobRepository(AnalysisJobRepository):
    async def create(self, analysis_job: AnalysisJob) -> AnalysisJob:
        raise SQLAlchemyError("forced persistence failure")


async def test_submission_rolls_back_on_persistence_failure(
    submission_session: AsyncSession,
) -> None:
    service = RepositorySubmissionService(
        session=submission_session,
        repositories=RepositoryRepository(submission_session),
        analysis_jobs=FailingAnalysisJobRepository(submission_session),
        pipeline_version="v1",
    )

    with pytest.raises(PersistenceError):
        await service.submit("https://github.com/acme/project")

    assert (
        await RepositoryRepository(submission_session).get_by_normalized_url(
            "https://github.com/acme/project"
        )
        is None
    )


class RacingRepositoryRepository(RepositoryRepository):
    def __init__(self, session: AsyncSession, existing: Repository) -> None:
        super().__init__(session)
        self._existing = existing
        self._lookup_count = 0

    async def get_by_normalized_url(self, normalized_url: str) -> Repository | None:
        self._lookup_count += 1
        return None if self._lookup_count == 1 else self._existing

    async def create(self, repository: Repository) -> Repository:
        raise IntegrityError(
            "INSERT INTO repositories",
            {},
            Exception("UNIQUE constraint failed: repositories.normalized_url"),
        )


class RecordingAnalysisJobRepository(AnalysisJobRepository):
    async def create(self, analysis_job: AnalysisJob) -> AnalysisJob:
        analysis_job.id = uuid4()
        return analysis_job


async def test_submission_recovers_once_from_normalized_url_uniqueness_race() -> None:
    session_mock = AsyncMock(spec=AsyncSession)
    session = cast(AsyncSession, session_mock)
    existing = Repository(
        id=uuid4(),
        source_url="https://github.com/acme/project",
        normalized_url="https://github.com/acme/project",
        owner="acme",
        name="project",
    )
    service = RepositorySubmissionService(
        session=session,
        repositories=RacingRepositoryRepository(session, existing),
        analysis_jobs=RecordingAnalysisJobRepository(session),
        pipeline_version="v1",
    )

    result = await service.submit("https://github.com/acme/project")

    assert result.repository is existing
    session_mock.rollback.assert_awaited_once()
    session_mock.commit.assert_awaited_once()
