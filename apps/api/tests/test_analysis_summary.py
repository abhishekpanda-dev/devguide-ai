from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AnalysisNotFoundError, AnalysisSummaryNotReadyError
from app.db.base import Base
from app.models import AnalysisJob, Repository
from app.parser import RepositoryParser
from app.repositories import AnalysisJobRepository, ParsedRepository, RepositoryRepository
from app.services.analysis_summary import AnalysisSummaryService
from app.services.parser_persistence import ParserPersistenceService


@pytest.fixture
async def summary_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def create_scope(session: AsyncSession) -> tuple[Repository, AnalysisJob]:
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


async def persist_directory(
    session: AsyncSession,
    repository: Repository,
    job: AnalysisJob,
    root: Path,
    *,
    limitations: tuple[str, ...] = (),
) -> None:
    result = RepositoryParser().parse(root)
    result = replace(
        result,
        statistics=replace(result.statistics, limitations=limitations),
    )
    await ParserPersistenceService(session).persist(
        repository_id=repository.id,
        analysis_job_id=job.id,
        commit_sha="a" * 40,
        result=result,
    )


async def test_summary_aggregates_persisted_counts_and_languages(
    summary_session: AsyncSession, tmp_path: Path
) -> None:
    repository, job = await create_scope(summary_session)
    (tmp_path / "tests").mkdir()
    (tmp_path / "main.py").write_text("one\ntwo\n", encoding="utf-8")
    (tmp_path / "tests" / "test_main.py").write_text("test\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("a\nb\nc\n", encoding="utf-8")
    (tmp_path / "ignored.bin").write_bytes(b"\x00\x01")
    await persist_directory(
        summary_session,
        repository,
        job,
        tmp_path,
        limitations=("ignored.bin: unsupported file was skipped.",),
    )

    summary = await AnalysisSummaryService(
        AnalysisJobRepository(summary_session), ParsedRepository(summary_session)
    ).get_required(job.id)

    assert summary.files_analyzed == 3
    assert summary.chunks_created == 3
    assert [(item.language, item.file_count, item.line_count) for item in summary.languages] == [
        ("markdown", 1, 3),
        ("python", 2, 3),
    ]
    assert summary.total_lines == 6
    assert summary.test_file_count == 1
    assert summary.documentation_file_count == 1
    assert summary.skipped_file_count == 1
    assert summary.limitations == ["ignored.bin: unsupported file was skipped."]


async def test_summary_is_isolated_to_requested_analysis(
    summary_session: AsyncSession, tmp_path: Path
) -> None:
    repository, first = await create_scope(summary_session)
    second = await AnalysisJobRepository(summary_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await summary_session.commit()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "main.py").write_text("one\ntwo\n", encoding="utf-8")
    (second_root / "index.ts").write_text("one\n", encoding="utf-8")
    await persist_directory(summary_session, repository, first, first_root)
    await persist_directory(summary_session, repository, second, second_root)

    service = AnalysisSummaryService(
        AnalysisJobRepository(summary_session), ParsedRepository(summary_session)
    )
    first_summary = await service.get_required(first.id)
    second_summary = await service.get_required(second.id)

    assert [(item.language, item.line_count) for item in first_summary.languages] == [
        ("python", 2)
    ]
    assert [(item.language, item.line_count) for item in second_summary.languages] == [
        ("typescript", 1)
    ]
    assert first_summary.analysis_job_id == first.id
    assert second_summary.analysis_job_id == second.id


async def test_summary_missing_analysis_is_not_found(summary_session: AsyncSession) -> None:
    _repository, job = await create_scope(summary_session)
    missing_id = job.id
    await summary_session.delete(job)
    await summary_session.commit()

    with pytest.raises(AnalysisNotFoundError):
        await AnalysisSummaryService(
            AnalysisJobRepository(summary_session), ParsedRepository(summary_session)
        ).get_required(missing_id)


async def test_summary_without_parser_metadata_is_not_ready(
    summary_session: AsyncSession,
) -> None:
    _repository, job = await create_scope(summary_session)

    with pytest.raises(AnalysisSummaryNotReadyError):
        await AnalysisSummaryService(
            AnalysisJobRepository(summary_session), ParsedRepository(summary_session)
        ).get_required(job.id)
