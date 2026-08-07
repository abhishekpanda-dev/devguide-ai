import hashlib
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ai.retrieval import SearchRepositorySkill
from app.db.base import Base
from app.models import AnalysisJob, CodeChunk, Repository, RepositoryFile
from app.repositories import AnalysisJobRepository, ParsedRepository, RepositoryRepository
from app.schemas.retrieval import MatchedChannel, SearchRepositoryRequest

COMMIT = "a" * 40


@pytest.fixture
async def search_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def analysis(session: AsyncSession, name: str) -> tuple[UUID, UUID]:
    repository = await RepositoryRepository(session).create(
        Repository(
            source_url=f"https://github.com/acme/{name}",
            normalized_url=f"https://github.com/acme/{name}",
            owner="acme",
            name=name,
            latest_commit_sha=COMMIT,
        )
    )
    job = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repository.id, pipeline_version="1")
    )
    await session.commit()
    return repository.id, job.id


def file_and_chunks(
    repository_id: UUID,
    job_id: UUID,
    path: str,
    language: str,
    chunks: list[tuple[str, int, int, str]],
) -> tuple[RepositoryFile, list[CodeChunk]]:
    file_id = uuid4()
    line_count = max(end for _, _, end, _ in chunks)
    file = RepositoryFile(
        id=file_id,
        repository_id=repository_id,
        analysis_job_id=job_id,
        commit_sha=COMMIT,
        path=path,
        file_name=path.rsplit("/", 1)[-1],
        extension=f".{path.rsplit('.', 1)[-1]}",
        language=language,
        size_bytes=sum(len(content) for _, _, _, content in chunks),
        line_count=line_count,
        content_hash="f" * 64,
        is_test=False,
        is_documentation=False,
        is_configuration=False,
        is_generated=False,
        limitations=[],
    )
    models = [
        CodeChunk(
            id=chunk_id,
            repository_file_id=file_id,
            analysis_job_id=job_id,
            commit_sha=COMMIT,
            start_line=start,
            end_line=end,
            content=content,
            language=language,
            parser_version="1",
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )
        for chunk_id, start, end, content in chunks
    ]
    return file, models


async def seed(search_session: AsyncSession) -> tuple[UUID, UUID]:
    repository_id, job_id = await analysis(search_session, "primary")
    files_and_chunks = [
        file_and_chunks(
            repository_id,
            job_id,
            "app/services/search.py",
            "python",
            [
                (
                    "search",
                    1,
                    8,
                    "class SearchService:\n"
                    "    def search_repository(self):\n"
                    "        return 'lexical content search'\n",
                )
            ],
        ),
        file_and_chunks(
            repository_id,
            job_id,
            "app/core/config.py",
            "python",
            [("config", 1, 5, "SEARCH_LIMIT = 10\napi.timeout: 30\n")],
        ),
        file_and_chunks(
            repository_id,
            job_id,
            "web/search.ts",
            "typescript",
            [("web", 1, 4, "function renderSearch() { return 'lexical'; }\n")],
        ),
    ]
    files = [item[0] for item in files_and_chunks]
    chunks = [chunk for item in files_and_chunks for chunk in item[1]]
    await ParsedRepository(search_session).replace(job_id, files, chunks)
    await search_session.commit()
    return repository_id, job_id


async def test_exact_and_partial_path_matching(search_session: AsyncSession) -> None:
    _repository_id, job_id = await seed(search_session)
    skill = SearchRepositorySkill(ParsedRepository(search_session))
    exact = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="app/services/search.py")
    )
    partial = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="services/search")
    )
    assert exact.evidence[0].path == "app/services/search.py"
    assert MatchedChannel.EXACT_PATH in exact.evidence[0].matched_channels
    assert partial.evidence[0].path == "app/services/search.py"
    assert MatchedChannel.PARTIAL_PATH in partial.evidence[0].matched_channels


async def test_phrase_token_and_symbol_ranking(search_session: AsyncSession) -> None:
    _repository_id, job_id = await seed(search_session)
    skill = SearchRepositorySkill(ParsedRepository(search_session))
    phrase = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="lexical content search")
    )
    tokens = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="lexical search repository")
    )
    symbol = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="SearchService")
    )
    config = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="api.timeout")
    )
    assert MatchedChannel.EXACT_PHRASE in phrase.evidence[0].matched_channels
    assert tokens.evidence[0].path == "app/services/search.py"
    assert MatchedChannel.TOKEN_OVERLAP in tokens.evidence[0].matched_channels
    assert MatchedChannel.SYMBOL in symbol.evidence[0].matched_channels
    assert MatchedChannel.SYMBOL in config.evidence[0].matched_channels


async def test_language_and_path_prefix_are_hard_filters(search_session: AsyncSession) -> None:
    _repository_id, job_id = await seed(search_session)
    skill = SearchRepositorySkill(ParsedRepository(search_session))
    language = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="lexical", languages=("typescript",))
    )
    prefix = await skill.search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="search", path_prefix="app/core")
    )
    assert [item.language for item in language.evidence] == ["typescript"]
    assert all(item.path.startswith("app/core/") for item in prefix.evidence)


async def test_analysis_and_repository_isolation(search_session: AsyncSession) -> None:
    _repository_id, job_id = await seed(search_session)
    other_repository_id, other_job_id = await analysis(search_session, "other")
    other_file, other_chunks = file_and_chunks(
        other_repository_id,
        other_job_id,
        "secret.py",
        "python",
        [("other", 1, 1, "cross_repository_secret = True")],
    )
    await ParsedRepository(search_session).replace(other_job_id, [other_file], other_chunks)
    await search_session.commit()
    result = await SearchRepositorySkill(ParsedRepository(search_session)).search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="cross_repository_secret")
    )
    assert result.evidence == ()
    assert result.total_candidates == 3


async def test_deterministic_ordering_and_minimum_score(search_session: AsyncSession) -> None:
    repository_id, job_id = await analysis(search_session, "ordering")
    first, first_chunks = file_and_chunks(
        repository_id, job_id, "a.py", "python", [("a", 1, 1, "target = True")]
    )
    second, second_chunks = file_and_chunks(
        repository_id, job_id, "b.py", "python", [("b", 1, 1, "target = False")]
    )
    await ParsedRepository(search_session).replace(
        job_id, [second, first], second_chunks + first_chunks
    )
    await search_session.commit()
    skill = SearchRepositorySkill(ParsedRepository(search_session))
    request = SearchRepositoryRequest(analysis_job_id=job_id, query="target")
    one = await skill.search(request)
    two = await skill.search(request)
    filtered = await skill.search(request.model_copy(update={"minimum_score": 100.0}))
    assert [item.path for item in one.evidence] == ["a.py", "b.py"]
    assert one == two
    assert filtered.evidence == ()
    assert "Insufficient" in filtered.limitations[0]


async def test_duplicate_and_overlapping_chunks_are_removed(search_session: AsyncSession) -> None:
    repository_id, job_id = await analysis(search_session, "duplicates")
    duplicate = "def target():\n    return True\n"
    file, chunks = file_and_chunks(
        repository_id,
        job_id,
        "target.py",
        "python",
        [
            ("strong", 1, 5, f"{duplicate}target = 1"),
            ("overlap", 4, 8, "target = 1\nmore = True"),
            ("identical", 10, 12, f"{duplicate}target = 1"),
        ],
    )
    await ParsedRepository(search_session).replace(job_id, [file], chunks)
    await search_session.commit()
    result = await SearchRepositorySkill(ParsedRepository(search_session)).search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="target")
    )
    assert len(result.evidence) == 1


def test_request_limit_and_path_validation() -> None:
    with pytest.raises(ValidationError):
        SearchRepositoryRequest(analysis_job_id=uuid4(), query="x", limit=0)
    with pytest.raises(ValidationError):
        SearchRepositoryRequest(analysis_job_id=uuid4(), query="x", limit=101)
    with pytest.raises(ValidationError):
        SearchRepositoryRequest(analysis_job_id=uuid4(), query="x", path_prefix="../escape")


async def test_invalid_citations_fail_closed(search_session: AsyncSession) -> None:
    repository_id, job_id = await analysis(search_session, "invalid")
    file, chunks = file_and_chunks(
        repository_id, job_id, "valid.py", "python", [("bad", 1, 2, "target = True")]
    )
    chunks[0].content_hash = "0" * 64
    await ParsedRepository(search_session).replace(job_id, [file], chunks)
    await search_session.commit()
    result = await SearchRepositorySkill(ParsedRepository(search_session)).search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="target")
    )
    assert result.evidence == ()


async def test_valid_citation_contains_persisted_provenance(search_session: AsyncSession) -> None:
    _repository_id, job_id = await seed(search_session)
    result = await SearchRepositorySkill(ParsedRepository(search_session)).search(
        SearchRepositoryRequest(analysis_job_id=job_id, query="SearchService", limit=1)
    )
    citation = result.evidence[0]
    assert citation.start_line >= 1
    assert citation.end_line >= citation.start_line
    assert not citation.path.startswith(("/", "\\"))
    assert citation.commit_sha == COMMIT
    assert citation.content_hash == hashlib.sha256(citation.excerpt.encode()).hexdigest()
