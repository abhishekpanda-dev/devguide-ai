from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import ApplicationValidationError, PersistenceError
from app.db.base import Base
from app.models import AnalysisJob, AnalysisParseMetadata, CodeChunk, Repository, RepositoryFile
from app.parser import RepositoryParser, RepositoryParseResult
from app.repositories import AnalysisJobRepository, ParsedRepository, RepositoryRepository
from app.services.parser_persistence import ParserPersistenceService


@pytest.fixture
async def persistence_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def scope(session: AsyncSession) -> tuple[Repository, AnalysisJob]:
    repository = await RepositoryRepository(session).create(
        Repository(
            source_url="https://github.com/acme/project",
            normalized_url="https://github.com/acme/project",
            owner="acme",
            name="project",
            latest_commit_sha="a" * 40,
        )
    )
    job = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await session.commit()
    return repository, job


def parsed(tmp_path: Path, content: str = "one\ntwo\n") -> RepositoryParseResult:
    (tmp_path / "source.py").write_text(content, encoding="utf-8")
    return RepositoryParser(maximum_lines_per_chunk=1, overlap_lines=0).parse(tmp_path)


async def test_persistence_stores_files_chunks_and_replaces_idempotently(
    persistence_session: AsyncSession, tmp_path: Path
) -> None:
    repository, job = await scope(persistence_session)
    service = ParserPersistenceService(persistence_session)
    first = await service.persist(
        repository_id=repository.id,
        analysis_job_id=job.id,
        commit_sha="a" * 40,
        result=parsed(tmp_path),
    )
    second = await service.persist(
        repository_id=repository.id,
        analysis_job_id=job.id,
        commit_sha="a" * 40,
        result=parsed(tmp_path, "changed\n"),
    )
    stored = ParsedRepository(persistence_session)
    files = await stored.list_files(job.id)
    chunks = await stored.list_chunks(job.id)
    assert (first.files_persisted, first.chunks_persisted) == (1, 2)
    assert (second.files_persisted, second.chunks_persisted) == (1, 1)
    assert len(files) == len(chunks) == 1
    assert files[0].path == "source.py"
    assert chunks[0].start_line == chunks[0].end_line == 1
    assert chunks[0].content == "changed"


async def test_absolute_paths_are_rejected(
    persistence_session: AsyncSession, tmp_path: Path
) -> None:
    repository, job = await scope(persistence_session)
    result = parsed(tmp_path)
    source = result.files[0]
    invalid = replace(
        result, files=(replace(source, metadata=replace(source.metadata, path="C:/secret.py")),)
    )
    with pytest.raises(ApplicationValidationError):
        await ParserPersistenceService(persistence_session).persist(
            repository_id=repository.id, analysis_job_id=job.id, commit_sha="a" * 40, result=invalid
        )


class FailingParsedRepository(ParsedRepository):
    async def replace(
        self,
        analysis_job_id: UUID,
        files: list[RepositoryFile],
        chunks: list[CodeChunk],
        metadata: AnalysisParseMetadata | None = None,
    ) -> None:
        raise SQLAlchemyError("forced")


async def test_persistence_rolls_back_on_failure(
    persistence_session: AsyncSession, tmp_path: Path
) -> None:
    repository, job = await scope(persistence_session)
    service = ParserPersistenceService(
        persistence_session, FailingParsedRepository(persistence_session)
    )
    with pytest.raises(PersistenceError):
        await service.persist(
            repository_id=repository.id,
            analysis_job_id=job.id,
            commit_sha="a" * 40,
            result=parsed(tmp_path),
        )
