from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisStage,
    Repository,
    RepositorySourceType,
    RepositoryStatus,
)
from app.repositories import AnalysisJobRepository, AnalysisStageRepository, RepositoryRepository


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def make_repository(url: str = "https://github.com/acme/project") -> Repository:
    return Repository(
        source_type=RepositorySourceType.GITHUB_PUBLIC,
        source_url=url,
        normalized_url=url,
        owner="acme",
        name="project",
        status=RepositoryStatus.PENDING,
    )


async def test_repository_create_read_and_list(db_session: AsyncSession) -> None:
    repository_store = RepositoryRepository(db_session)
    created = await repository_store.create(make_repository())

    assert await repository_store.get_by_id(created.id) is created
    assert await repository_store.get_by_normalized_url(created.normalized_url) is created
    assert await repository_store.list(limit=10, offset=0) == [created]


async def test_repository_normalized_url_is_unique(db_session: AsyncSession) -> None:
    repository_store = RepositoryRepository(db_session)
    await repository_store.create(make_repository())
    with pytest.raises(IntegrityError):
        await repository_store.create(make_repository())
    await db_session.rollback()


async def test_analysis_job_status_and_progress_updates(db_session: AsyncSession) -> None:
    repository = await RepositoryRepository(db_session).create(make_repository())
    job_store = AnalysisJobRepository(db_session)
    job = await job_store.create(
        AnalysisJob(repository_id=repository.id, pipeline_version="v1", progress_percent=0)
    )

    updated_status = await job_store.update_status(job.id, AnalysisJobStatus.RUNNING)
    updated_progress = await job_store.update_progress(job.id, 50)

    assert updated_status is not None and updated_status.status is AnalysisJobStatus.RUNNING
    assert updated_progress is not None and updated_progress.progress_percent == 50
    assert await job_store.list_for_repository(repository.id) == [job]


async def test_analysis_job_database_progress_constraint(db_session: AsyncSession) -> None:
    repository = await RepositoryRepository(db_session).create(make_repository())
    job = await AnalysisJobRepository(db_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="v1")
    )
    with pytest.raises(IntegrityError):
        await AnalysisJobRepository(db_session).update_progress(job.id, 101)
    await db_session.rollback()


async def test_analysis_stage_creation_progress_and_heartbeat(db_session: AsyncSession) -> None:
    repository = await RepositoryRepository(db_session).create(make_repository())
    job = await AnalysisJobRepository(db_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="v1")
    )
    stage_store = AnalysisStageRepository(db_session)
    stage = await stage_store.create(AnalysisStage(analysis_job_id=job.id, name="inventory"))
    heartbeat = datetime.now(UTC)

    updated_progress = await stage_store.update_progress(stage.id, 75)
    updated_heartbeat = await stage_store.update_heartbeat(stage.id, heartbeat)

    assert updated_progress is not None and updated_progress.progress_percent == 75
    assert updated_heartbeat is not None and updated_heartbeat.heartbeat_at == heartbeat
    assert await stage_store.list_for_analysis_job(job.id) == [stage]


async def test_analysis_stage_database_progress_constraint(db_session: AsyncSession) -> None:
    repository = await RepositoryRepository(db_session).create(make_repository())
    job = await AnalysisJobRepository(db_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="v1")
    )
    stage = await AnalysisStageRepository(db_session).create(
        AnalysisStage(analysis_job_id=job.id, name="inventory")
    )
    with pytest.raises(IntegrityError):
        await AnalysisStageRepository(db_session).update_progress(stage.id, -1)
    await db_session.rollback()


async def test_foreign_key_prevents_deleting_referenced_parent(db_session: AsyncSession) -> None:
    repository = await RepositoryRepository(db_session).create(make_repository())
    await AnalysisJobRepository(db_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="v1")
    )
    await db_session.delete(repository)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
