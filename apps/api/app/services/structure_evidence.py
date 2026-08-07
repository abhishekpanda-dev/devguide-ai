import re
from collections import Counter
from pathlib import PurePosixPath
from typing import Protocol
from uuid import UUID

from app.models import RepositoryFile, RepositoryFileIntelligence
from app.repositories.structure import StructureRecord
from app.schemas.structure_evidence import StructureEdgeFact, StructureEvidence, StructureFileFact

_ARCHITECTURE_TERMS = re.compile(
    r"\b(architecture|entry\s*points?|module|dependenc(?:y|ies)|depends?\s+on|used(?:\s+by)?|"
    r"data\s+flow|service\s+layer|most\s+connected|coupling|imports?|requires?|reexports?)\b",
    re.IGNORECASE,
)
_PATH = re.compile(r"(?<![\w.-])([\w.-]+(?:/[\w.-]+)+\.[A-Za-z0-9]+|[\w.-]+\.[A-Za-z0-9]+)")


def is_structure_question(question: str) -> bool:
    return _ARCHITECTURE_TERMS.search(question) is not None


class StructureEvidenceRepository(Protocol):
    async def get(
        self,
        analysis_id: UUID,
        *,
        edge_limit: int | None = None,
        related_paths: tuple[str, ...] = (),
    ) -> StructureRecord | None: ...


class StructureEvidenceService:
    def __init__(
        self,
        repository: StructureEvidenceRepository,
        *,
        file_limit: int = 8,
        edge_limit: int = 12,
        directory_limit: int = 8,
    ) -> None:
        self._repository = repository
        self._file_limit = file_limit
        self._edge_limit = edge_limit
        self._directory_limit = directory_limit

    async def retrieve(self, analysis_id: UUID, question: str) -> StructureEvidence | None:
        if not is_structure_question(question):
            return None
        requested_paths = tuple(dict.fromkeys(_PATH.findall(question)))
        record = await self._repository.get(
            analysis_id,
            edge_limit=self._edge_limit,
            related_paths=requested_paths,
        )
        if record is None:
            return StructureEvidence(
                analysis_job_id=analysis_id,
                limitations=("Persisted structure evidence is unavailable.",),
            )
        rows = record.files
        facts = {file.id: self._fact(file, intelligence) for file, intelligence in rows}
        languages = Counter(file.language for file, _ in rows)
        directories = Counter(
            (PurePosixPath(file.path).parts[0] if len(PurePosixPath(file.path).parts) > 1 else ".")
            for file, _ in rows
        )
        relevant_edges = list(record.edges)
        by_inbound = sorted(facts.values(), key=lambda item: (-item.inbound_count, item.path))
        by_outbound = sorted(facts.values(), key=lambda item: (-item.outbound_count, item.path))
        connected = sorted(
            facts.values(),
            key=lambda item: (-(item.inbound_count + item.outbound_count), item.path),
        )
        limitations = list(record.metadata.limitations)
        limitations.append(
            "Dependency edges are static relationships and do not prove runtime behavior."
        )
        limitations.append(
            "Probable entry points are heuristic candidates, not confirmed runtime entry points."
        )
        if requested_paths and not relevant_edges:
            limitations.append(
                "No resolved local dependency edge matched the requested file or module."
            )
        return StructureEvidence(
            analysis_job_id=analysis_id,
            language_counts=dict(sorted(languages.items())),
            directory_counts=dict(directories.most_common(self._directory_limit)),
            probable_entry_points=tuple(
                sorted(
                    (item for item in facts.values() if item.is_probable_entry_point),
                    key=lambda item: (-item.entry_point_confidence, item.path),
                )[: self._file_limit]
            ),
            highest_inbound=tuple(item for item in by_inbound if item.inbound_count > 0)[
                : self._file_limit
            ],
            highest_outbound=tuple(item for item in by_outbound if item.outbound_count > 0)[
                : self._file_limit
            ],
            most_connected=tuple(
                item for item in connected if item.inbound_count + item.outbound_count > 0
            )[: self._file_limit],
            dependency_edges=tuple(
                StructureEdgeFact.model_validate(edge, from_attributes=True)
                for edge in relevant_edges[: self._edge_limit]
            ),
            limitations=tuple(dict.fromkeys(limitations)),
        )

    @staticmethod
    def _fact(file: RepositoryFile, intelligence: RepositoryFileIntelligence) -> StructureFileFact:
        return StructureFileFact(
            repository_file_id=file.id,
            path=file.path,
            language=file.language,
            classification=intelligence.classification,
            inbound_count=intelligence.inbound_dependency_count,
            outbound_count=intelligence.outbound_dependency_count,
            is_probable_entry_point=intelligence.is_entry_point,
            entry_point_reason=intelligence.entry_point_reason,
            entry_point_confidence=intelligence.entry_point_confidence,
        )
