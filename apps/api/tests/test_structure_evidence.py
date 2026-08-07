from types import SimpleNamespace
from typing import cast
from uuid import uuid4

from app.repositories.structure import StructureRecord
from app.services.structure_evidence import StructureEvidenceService, is_structure_question


def _file(path: str, language: str = "python") -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), path=path, language=language)


def _intelligence(*, inbound: int = 0, outbound: int = 0, entry: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        classification="source",
        inbound_dependency_count=inbound,
        outbound_dependency_count=outbound,
        is_entry_point=entry,
        entry_point_reason="conventional filename" if entry else None,
        entry_point_confidence=0.8 if entry else 0,
    )


class FakeStructureRepository:
    def __init__(self, record: StructureRecord | None) -> None:
        self.record = record
        self.calls: list[tuple[object, int | None, tuple[str, ...]]] = []

    async def get(
        self,
        analysis_id: object,
        *,
        edge_limit: int | None = None,
        related_paths: tuple[str, ...] = (),
    ) -> StructureRecord | None:
        self.calls.append((analysis_id, edge_limit, related_paths))
        return self.record


def test_architecture_intent_is_deterministic_and_avoids_unrelated_noise() -> None:
    assert is_structure_question("What are the probable entry points?")
    assert is_structure_question("What depends on app/main.py?")
    assert is_structure_question("Which files have the most coupling?")
    assert not is_structure_question("Why is this variable named result?")


async def test_non_architecture_question_does_not_query_structure() -> None:
    repository = FakeStructureRepository(None)
    result = await StructureEvidenceService(repository).retrieve(uuid4(), "Explain this function")
    assert result is None
    assert repository.calls == []


async def test_structure_evidence_is_bounded_and_contains_static_limitations() -> None:
    main = _file("app/main.py")
    service = _file("app/service.py")
    edge = SimpleNamespace(
        source_path="app/main.py",
        target_path="app/service.py",
        relationship_type="imports",
        module_name="app.service",
        source_line=3,
        confidence=1,
    )
    record = SimpleNamespace(
        files=((main, _intelligence(outbound=1, entry=True)), (service, _intelligence(inbound=1))),
        edges=(edge, edge),
        metadata=SimpleNamespace(limitations=["Dynamic imports are unresolved."]),
    )
    repository = FakeStructureRepository(cast(StructureRecord, record))
    evidence = await StructureEvidenceService(
        repository, file_limit=1, edge_limit=1, directory_limit=1
    ).retrieve(uuid4(), "What does app/main.py depend on?")
    assert evidence is not None
    assert len(evidence.probable_entry_points) == 1
    assert len(evidence.most_connected) == 1
    assert len(evidence.dependency_edges) == 1
    assert evidence.dependency_edges[0].source_line == 3
    assert repository.calls[0][1:] == (1, ("app/main.py",))
    assert any("runtime behavior" in item for item in evidence.limitations)
    assert any("heuristic" in item for item in evidence.limitations)


async def test_unresolved_dependency_query_returns_a_limitation() -> None:
    record = SimpleNamespace(
        files=((_file("app/main.py"), _intelligence(entry=True)),),
        edges=(),
        metadata=SimpleNamespace(limitations=[]),
    )
    evidence = await StructureEvidenceService(
        FakeStructureRepository(cast(StructureRecord, record))
    ).retrieve(uuid4(), "Where is missing.py used?")
    assert evidence is not None
    assert any("No resolved local dependency edge" in item for item in evidence.limitations)
