from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import AnalysisJob, AnalysisStructureMetadata, Repository, RepositoryDependencyEdge
from app.parser import RepositoryParser
from app.repositories import (
    AnalysisJobRepository,
    RepositoryRepository,
    RepositoryStructureRepository,
)
from app.services.parser_persistence import ParserPersistenceService
from app.services.structure import RepositoryStructurePersistenceService, RepositoryStructureService
from app.structure import RepositoryStructureExtractor


@pytest.fixture
async def structure_session() -> AsyncIterator[AsyncSession]:
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
    analysis = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await session.commit()
    return repository, analysis


async def persist_structure(
    session: AsyncSession, repository: Repository, analysis: AnalysisJob, root: Path
) -> None:
    parsed = RepositoryParser().parse(root)
    await ParserPersistenceService(session).persist(
        repository_id=repository.id, analysis_job_id=analysis.id, commit_sha="a" * 40, result=parsed
    )
    structure = RepositoryStructureExtractor(maximum_edges=100).analyze(parsed)
    await RepositoryStructurePersistenceService(session).persist(analysis.id, structure)


def write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


async def test_persistence_is_idempotent_counts_filters_helpers_and_source_url(
    structure_session: AsyncSession, tmp_path: Path
) -> None:
    repository, analysis = await create_scope(structure_session)
    write(tmp_path, "app/main.py", "import app.service\nif __name__ == '__main__':\n    run()\n")
    write(tmp_path, "app/service.py", "value = 1\n")
    await persist_structure(structure_session, repository, analysis, tmp_path)
    await persist_structure(structure_session, repository, analysis, tmp_path)
    structures = RepositoryStructureRepository(structure_session)
    record = await structures.get(analysis.id)
    assert record is not None
    assert len(record.edges) == 1
    source = next(info for file, info in record.files if file.path == "app/main.py")
    target = next(info for file, info in record.files if file.path == "app/service.py")
    assert source.outbound_dependency_count == 1 and source.inbound_dependency_count == 0
    assert target.inbound_dependency_count == 1 and target.outbound_dependency_count == 0
    assert len(await structures.dependencies_of(analysis.id, source.repository_file_id)) == 1
    assert len(await structures.dependents_of(analysis.id, target.repository_file_id)) == 1
    assert len(await structures.probable_entry_points(analysis.id)) == 1
    assert len(await structures.most_connected(analysis.id, limit=1)) == 1
    assert len(await structures.files_by_language(analysis.id, "python")) == 2
    assert len(await structures.files_under_prefix(analysis.id, "app/")) == 2
    response = await RepositoryStructureService(
        AnalysisJobRepository(structure_session),
        RepositoryRepository(structure_session),
        structures,
    ).get_required(
        analysis.id, language="python", path_prefix="app", relationship_type="imports", limit=10
    )
    assert response.summary.edge_count == 1
    assert response.summary.file_count == 2
    assert response.summary.entry_point_count == 1
    assert response.dependency_edges[0].source_line == 1
    assert (
        str(response.dependency_edges[0].source_url)
        == f"https://github.com/acme/project/blob/{'a' * 40}/app/main.py#L1"
    )
    assert await structure_session.scalar(select(func.count(RepositoryDependencyEdge.id))) == 1


async def test_zero_edge_metadata_and_analysis_isolation(
    structure_session: AsyncSession, tmp_path: Path
) -> None:
    repository, first = await create_scope(structure_session)
    second = await AnalysisJobRepository(structure_session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await structure_session.commit()
    first_root, second_root = tmp_path / "first", tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    write(first_root, "plain.py", "value = 1\n")
    write(second_root, "target.py", "value = 1\n")
    write(second_root, "source.py", "import target\n")
    await persist_structure(structure_session, repository, first, first_root)
    await persist_structure(structure_session, repository, second, second_root)
    structures = RepositoryStructureRepository(structure_session)
    first_record, second_record = await structures.get(first.id), await structures.get(second.id)
    assert first_record is not None and first_record.edges == ()
    assert second_record is not None and len(second_record.edges) == 1
    assert await structure_session.get(AnalysisStructureMetadata, first.id) is not None
