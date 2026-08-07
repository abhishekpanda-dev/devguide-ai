# mypy: ignore-errors
from types import SimpleNamespace
from uuid import uuid4

from app.models import RepositoryDependencyEdge, RepositoryFile, RepositoryFileIntelligence
from app.repositories.structure import StructureRecord
from app.services.feature_location import (
    FeatureLocationService,
    extract_feature_phrase,
    is_feature_location_question,
)

ANALYSIS_ID = uuid4()
REPOSITORY_ID = uuid4()
COMMIT = "a" * 40


def file(path: str, *, is_test: bool = False) -> RepositoryFile:
    return RepositoryFile(
        id=uuid4(),
        repository_id=REPOSITORY_ID,
        analysis_job_id=ANALYSIS_ID,
        commit_sha=COMMIT,
        path=path,
        file_name=path.rsplit("/", 1)[-1],
        extension=".py",
        language="python",
        size_bytes=10,
        line_count=20,
        content_hash="b" * 64,
        is_test=is_test,
        is_documentation=False,
        is_configuration=False,
        is_generated=False,
        limitations=[],
    )


def info(
    item: RepositoryFile, *, entry: bool = False, inbound: int = 0, outbound: int = 0
) -> RepositoryFileIntelligence:
    return RepositoryFileIntelligence(
        analysis_job_id=ANALYSIS_ID,
        repository_file_id=item.id,
        classification="source",
        is_entry_point=entry,
        entry_point_reason="probable route" if entry else None,
        entry_point_confidence=0.8 if entry else 0,
        inbound_dependency_count=inbound,
        outbound_dependency_count=outbound,
    )


class Repository:
    def __init__(self, value):
        self.value = value

    async def get_by_id(self, _identifier):
        return self.value


class Structures:
    def __init__(self, record):
        self.record = record

    async def get(self, analysis_id, **_kwargs):
        assert analysis_id == ANALYSIS_ID
        return self.record


class Parsed:
    def __init__(self, chunks):
        self.chunks = chunks

    async def list_chunks(self, analysis_id):
        assert analysis_id == ANALYSIS_ID
        return self.chunks


class Findings:
    async def list_for_analysis(self, analysis_id, **_kwargs):
        assert analysis_id == ANALYSIS_ID
        return None


class Quality:
    async def get(self, analysis_id, **_kwargs):
        assert analysis_id == ANALYSIS_ID
        return None


def edge(source: RepositoryFile, target: RepositoryFile) -> RepositoryDependencyEdge:
    return RepositoryDependencyEdge(
        analysis_job_id=ANALYSIS_ID,
        source_repository_file_id=source.id,
        target_repository_file_id=target.id,
        relationship_type="imports",
        module_name=target.path,
        source_path=source.path,
        target_path=target.path,
        source_line=1,
        confidence=0.9,
    )


def test_intent_routing_and_bounded_normalization() -> None:
    assert is_feature_location_question("Where is repository submission implemented?")
    assert is_feature_location_question("What would be affected if I change auth service?")
    assert not is_feature_location_question("Why is this variable named result?")
    assert (
        extract_feature_phrase("Where should I modify Repository submission?")
        == "repository submission"
    )
    assert (
        extract_feature_phrase(
            "Where is realtime monitoring implemented, what could be affected, "
            "and which tests should I review?"
        )
        == "realtime monitoring"
    )
    assert (
        len(extract_feature_phrase("where is one two three four five six seven eight nine").split())
        == 8
    )


async def test_ranking_dependency_impact_tests_ordering_and_isolation() -> None:
    route = file("app/api/repository_submission.py")
    service_file = file("app/services/submission.py")
    model = file("app/models/repository.py")
    test_file = file("tests/test_repository_submission.py", is_test=True)
    other = file("app/unrelated.py")
    rows = (
        (route, info(route, entry=True, outbound=1)),
        (service_file, info(service_file, inbound=1, outbound=1)),
        (model, info(model, inbound=1)),
        (test_file, info(test_file)),
        (other, info(other)),
    )
    chunks = [
        SimpleNamespace(repository_file_id=route.id, content="repository submission route"),
        SimpleNamespace(repository_file_id=service_file.id, content="submission service"),
        SimpleNamespace(repository_file_id=test_file.id, content="repository submission test"),
    ]
    record = StructureRecord(
        SimpleNamespace(limitations=[]),
        rows,
        (edge(route, service_file), edge(service_file, model), edge(test_file, route)),
    )
    service = FeatureLocationService(
        Repository(SimpleNamespace(repository_id=REPOSITORY_ID)),
        Parsed(chunks),
        Structures(record),
        Repository(SimpleNamespace(normalized_url="https://github.com/example/project")),
        Findings(),
        Quality(),
        maximum_files=2,
        neighbor_depth=2,
        related_tests_limit=1,
    )
    result = await service.retrieve(
        ANALYSIS_ID, "What would be affected if I change repository submission?"
    )
    assert result is not None
    assert result.likely_files[0].path == "app/api/repository_submission.py"
    assert all(item.repository_file_id != other.id for item in result.likely_files)
    assert result.impact_summary.direct_dependencies
    assert result.impact_summary.probable_indirect
    assert result.impact_summary.probable_entry_points
    assert [item.path for item in result.related_tests] == ["tests/test_repository_submission.py"]
    assert result.related_tests[0].reason.endswith("coverage is not proven.")
    assert len(result.likely_files) <= 2 and len(result.related_tests) <= 1
    assert list(result.likely_files) == sorted(
        result.likely_files, key=lambda item: (-item.confidence, item.path)
    )
    assert all(
        str(item.source_url).startswith("https://github.com/example/project/blob/")
        for item in result.likely_files
    )


async def test_non_feature_question_does_not_touch_persistence() -> None:
    class Never:
        def __getattr__(self, _name):
            raise AssertionError("persistence should not be queried")

    service = FeatureLocationService(Never(), Never(), Never(), Never(), Never(), Never())
    assert await service.retrieve(ANALYSIS_ID, "Explain this variable name") is None
