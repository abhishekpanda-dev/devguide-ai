from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AnalysisNotFoundError, CodeFindingsNotReadyError, PersistenceError
from app.db.base import Base
from app.findings import DeterministicFindingsAnalyzer
from app.models import AnalysisJob, CodeFinding, FindingCategory, FindingSeverity, Repository
from app.parser import RepositoryParser, RepositoryParseResult
from app.repositories import AnalysisJobRepository, CodeFindingRepository, RepositoryRepository
from app.services.finding import CodeFindingPersistenceService, CodeFindingService
from app.services.parser_persistence import ParserPersistenceService


def analyzer(limit: int = 100, threshold: int = 1000) -> DeterministicFindingsAnalyzer:
    return DeterministicFindingsAnalyzer(
        large_file_line_threshold=threshold, maximum_findings=limit
    )


def parse(tmp_path: Path, content: str) -> RepositoryParseResult:
    (tmp_path / "source.py").write_text(content, encoding="utf-8")
    return RepositoryParser().parse(tmp_path)


def test_all_deterministic_rules_and_exact_lines(tmp_path: Path) -> None:
    content = (
        "import requests\nimport subprocess\n# TODO one\n# FIXME two\n# HACK three\n"
        "eval(x)\nexec(x)\nsubprocess.run(x, shell=True)\nrequests.get(url)\n"
        "DEBUG = True\ntry:\n x()\nexcept Exception:\n pass\n"
    )
    result = analyzer(threshold=14).analyze(parse(tmp_path, content), commit_sha="a" * 40)
    by = {x.rule_id: x for x in result.findings}
    expected = {
        "maintainability.todo",
        "maintainability.fixme",
        "maintainability.hack",
        "python.eval",
        "python.exec",
        "python.subprocess-shell",
        "network.missing-timeout",
        "security.debug-enabled",
        "python.broad-exception",
        "python.empty-exception",
        "maintainability.large-file",
    }
    assert expected == set(by)
    assert by["python.eval"].start_line == 6
    assert by["python.empty-exception"].start_line == 13
    assert all(x.path == "source.py" and x.end_line >= x.start_line >= 1 for x in result.findings)


def test_secret_is_redacted_and_safe_timeout_not_flagged(tmp_path: Path) -> None:
    secret = "real-secret-value"
    result = analyzer().analyze(
        parse(tmp_path, f'API_KEY = "{secret}"\nrequests.get(url, timeout=5)\n'),
        commit_sha="a" * 40,
    )
    assert len(result.findings) == 1
    assert result.findings[0].evidence_excerpt == 'API_KEY = "[REDACTED]"'
    assert secret not in repr(result)


def test_invalid_path_and_bound_fail_closed(tmp_path: Path) -> None:
    parsed = parse(tmp_path, "# TODO a\n# TODO b\n")
    source = parsed.files[0]
    unsafe = replace(
        parsed, files=(replace(source, metadata=replace(source.metadata, path="../x.py")),)
    )
    with pytest.raises(ValueError):
        analyzer().analyze(unsafe, commit_sha="a" * 40)
    bounded = analyzer(limit=1).analyze(parsed, commit_sha="a" * 40)
    assert len(bounded.findings) == 1 and bounded.limitations


@pytest.mark.parametrize(
    "lockfile",
    [
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Cargo.lock",
        "composer.lock",
    ],
)
def test_dependency_lockfiles_do_not_trigger_large_file(tmp_path: Path, lockfile: str) -> None:
    (tmp_path / lockfile).write_text(
        "# TODO retain other rules\n" + "entry\n" * 20, encoding="utf-8"
    )
    result = analyzer(threshold=10).analyze(RepositoryParser().parse(tmp_path), commit_sha="a" * 40)
    rule_ids = {item.rule_id for item in result.findings}
    assert "maintainability.large-file" not in rule_ids
    if lockfile == "package-lock.json":
        assert "maintainability.todo" in rule_ids


def test_large_application_source_still_triggers_large_file(tmp_path: Path) -> None:
    result = analyzer(threshold=10).analyze(
        parse(tmp_path, "value = 1\n" * 20), commit_sha="a" * 40
    )
    assert [item.rule_id for item in result.findings] == ["maintainability.large-file"]


@pytest.mark.parametrize("directory", ["node_modules", "dist", "build", "vendor"])
def test_excluded_directories_do_not_trigger_large_file(tmp_path: Path, directory: str) -> None:
    parsed = parse(tmp_path, "value = 1\n" * 20)
    source = parsed.files[0]
    excluded = replace(
        parsed,
        files=(
            replace(
                source,
                metadata=replace(source.metadata, path=f"{directory}/large.py"),
            ),
        ),
    )
    result = analyzer(threshold=10).analyze(excluded, commit_sha="a" * 40)
    assert "maintainability.large-file" not in {item.rule_id for item in result.findings}


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def scope(session: AsyncSession) -> tuple[Repository, AnalysisJob]:
    repo = await RepositoryRepository(session).create(
        Repository(
            source_url="https://github.com/acme/project",
            normalized_url="https://github.com/acme/project",
            owner="acme",
            name="project",
            latest_commit_sha="a" * 40,
        )
    )
    job = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repo.id, pipeline_version="1")
    )
    await session.commit()
    return repo, job


async def persist(session: AsyncSession, repo: Repository, job: AnalysisJob, root: Path) -> None:
    parsed = RepositoryParser().parse(root)
    await ParserPersistenceService(session).persist(
        repository_id=repo.id, analysis_job_id=job.id, commit_sha="a" * 40, result=parsed
    )
    await CodeFindingPersistenceService(session).persist(
        job.id, analyzer().analyze(parsed, commit_sha="a" * 40)
    )


def svc(session: AsyncSession) -> CodeFindingService:
    return CodeFindingService(
        AnalysisJobRepository(session),
        RepositoryRepository(session),
        CodeFindingRepository(session),
    )


async def test_persistence_filters_idempotency_redaction_and_url(
    session: AsyncSession, tmp_path: Path
) -> None:
    repo, job = await scope(session)
    secret = "must-never-leak"
    (tmp_path / "config.py").write_text(f'# TODO fix\nAPI_KEY = "{secret}"\n', encoding="utf-8")
    await persist(session, repo, job, tmp_path)
    await persist(session, repo, job, tmp_path)
    response = await svc(session).list_required(
        job.id,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.SECURITY,
        path_prefix=None,
        limit=10,
    )
    assert response.total_count == 1
    item = response.findings[0]
    assert item.start_line == 2
    assert str(item.source_url) == f"https://github.com/acme/project/blob/{'a' * 40}/config.py#L2"
    assert secret not in item.evidence_excerpt
    assert len((await session.scalars(select(CodeFinding))).all()) == 2


async def test_isolation_empty_missing_and_not_ready(session: AsyncSession, tmp_path: Path) -> None:
    repo, first = await scope(session)
    second = await AnalysisJobRepository(session).create(
        AnalysisJob(repository_id=repo.id, pipeline_version="1")
    )
    await session.commit()
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "a.py").write_text("# TODO x\n", encoding="utf-8")
    (b / "b.py").write_text("eval(x)\n", encoding="utf-8")
    await persist(session, repo, first, a)
    with pytest.raises(CodeFindingsNotReadyError):
        await svc(session).list_required(
            second.id, severity=None, category=None, path_prefix=None, limit=10
        )
    await persist(session, repo, second, b)
    one = await svc(session).list_required(
        first.id, severity=None, category=None, path_prefix=None, limit=10
    )
    two = await svc(session).list_required(
        second.id, severity=None, category=None, path_prefix=None, limit=10
    )
    assert [x.rule_id for x in one.findings] == ["maintainability.todo"]
    assert [x.rule_id for x in two.findings] == ["python.eval"]
    with pytest.raises(AnalysisNotFoundError):
        await svc(session).list_required(
            uuid4(), severity=None, category=None, path_prefix=None, limit=10
        )


def test_unsafe_github_path_rejected() -> None:
    with pytest.raises(PersistenceError):
        CodeFindingService.source_url("https://github.com/a/b", "a" * 40, "../x", 1, 1)
