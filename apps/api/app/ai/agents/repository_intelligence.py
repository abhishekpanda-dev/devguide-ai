from pathlib import PurePosixPath, PureWindowsPath
from typing import Protocol

from app.core.exceptions import (
    AppError,
    RepositoryAgentAnswerFailedError,
    RepositoryAgentEvidenceInvalidError,
    RepositoryAgentSearchFailedError,
)
from app.schemas.grounded_answer import EvidenceQuality, GroundedAnswer
from app.schemas.repository_agent import (
    RepositoryAgentCitation,
    RepositoryAgentRequest,
    RepositoryAgentResponse,
)
from app.schemas.retrieval import (
    RepositoryEvidence,
    SearchRepositoryRequest,
    SearchRepositoryResult,
)


class SearchSkill(Protocol):
    async def search(self, request: SearchRepositoryRequest) -> SearchRepositoryResult: ...


class GroundedAnswerGenerator(Protocol):
    async def answer(
        self,
        *,
        question: str,
        search_result: SearchRepositoryResult,
        correlation_id: str | None = None,
        maximum_citations: int = 10,
    ) -> GroundedAnswer: ...


class RepositoryIntelligenceAgent:
    """Bounded orchestration over retrieval and grounded generation only."""

    def __init__(self, search_skill: SearchSkill, answer_service: GroundedAnswerGenerator) -> None:
        self._search_skill = search_skill
        self._answer_service = answer_service

    async def run(self, request: RepositoryAgentRequest) -> RepositoryAgentResponse:
        search_request = SearchRepositoryRequest(
            analysis_job_id=request.analysis_job_id,
            query=request.question,
            languages=request.languages,
            path_prefix=request.path_prefix,
            limit=request.retrieval_limit,
            minimum_score=request.retrieval_minimum_score,
        )
        try:
            search_result = await self._search_skill.search(search_request)
        except Exception as exc:
            raise RepositoryAgentSearchFailedError from exc
        if search_result.analysis_job_id != request.analysis_job_id:
            raise RepositoryAgentEvidenceInvalidError
        if (
            search_result.returned_count != len(search_result.evidence)
            or search_result.returned_count > search_result.total_candidates
        ):
            raise RepositoryAgentEvidenceInvalidError
        evidence = self._validate_and_normalize_evidence(
            search_result.evidence, request.retrieval_limit
        )
        normalized_search = search_result.model_copy(
            update={
                "evidence": evidence,
                "returned_count": len(evidence),
            }
        )
        if not evidence:
            return RepositoryAgentResponse(
                analysis_job_id=request.analysis_job_id,
                question=request.question,
                answer="The persisted repository evidence is insufficient to answer this question.",
                citations=(),
                insufficient_evidence=True,
                evidence_quality=EvidenceQuality.INSUFFICIENT,
                retrieved_evidence_count=0,
                provider=None,
                model=None,
                limitations=search_result.limitations
                or ("No validated repository evidence met the retrieval threshold.",),
                correlation_id=request.correlation_id,
            )
        try:
            grounded = await self._answer_service.answer(
                question=request.question,
                search_result=normalized_search,
                correlation_id=request.correlation_id,
                maximum_citations=request.maximum_citations,
            )
        except AppError as exc:
            raise RepositoryAgentAnswerFailedError from exc
        except Exception as exc:
            raise RepositoryAgentAnswerFailedError from exc
        citations = self._validate_answer_citations(grounded, evidence)
        limitations = tuple(dict.fromkeys((*search_result.limitations, *grounded.limitations)))
        return RepositoryAgentResponse(
            analysis_job_id=request.analysis_job_id,
            question=request.question,
            answer=grounded.answer,
            citations=citations,
            insufficient_evidence=grounded.insufficient_evidence,
            evidence_quality=grounded.evidence_quality,
            retrieved_evidence_count=len(evidence),
            provider=None if grounded.provider == "none" else grounded.provider,
            model=None if grounded.model == "none" else grounded.model,
            limitations=limitations,
            correlation_id=request.correlation_id,
        )

    @staticmethod
    def _validate_and_normalize_evidence(
        evidence: tuple[RepositoryEvidence, ...], limit: int
    ) -> tuple[RepositoryEvidence, ...]:
        unique: dict[str, RepositoryEvidence] = {}
        for item in evidence:
            path = PurePosixPath(item.path)
            if (
                not item.chunk_id
                or not item.content_hash
                or not item.commit_sha
                or not item.path
                or "\\" in item.path
                or path.is_absolute()
                or PureWindowsPath(item.path).is_absolute()
                or ".." in path.parts
                or item.start_line < 1
                or item.end_line < item.start_line
            ):
                raise RepositoryAgentEvidenceInvalidError
            existing = unique.get(item.chunk_id)
            if existing is not None and existing != item:
                raise RepositoryAgentEvidenceInvalidError
            unique[item.chunk_id] = item
        ordered = sorted(
            unique.values(),
            key=lambda item: (
                -item.score,
                item.path,
                item.start_line,
                item.end_line,
                item.chunk_id,
            ),
        )
        return tuple(ordered[:limit])

    @staticmethod
    def _validate_answer_citations(
        grounded: GroundedAnswer, evidence: tuple[RepositoryEvidence, ...]
    ) -> tuple[RepositoryAgentCitation, ...]:
        available = {item.chunk_id: item for item in evidence}
        citations: list[RepositoryAgentCitation] = []
        seen: set[str] = set()
        for citation in grounded.citations:
            item = available.get(citation.chunk_id)
            if (
                item is None
                or citation.path != item.path
                or citation.start_line != item.start_line
                or citation.end_line != item.end_line
                or citation.content_hash != item.content_hash
            ):
                raise RepositoryAgentEvidenceInvalidError
            if item.chunk_id in seen:
                continue
            seen.add(item.chunk_id)
            citations.append(
                RepositoryAgentCitation(
                    chunk_id=item.chunk_id,
                    repository_file_id=item.repository_file_id,
                    path=item.path,
                    start_line=item.start_line,
                    end_line=item.end_line,
                    content_hash=item.content_hash,
                )
            )
        if grounded.insufficient_evidence and citations:
            raise RepositoryAgentEvidenceInvalidError
        if not grounded.insufficient_evidence and not citations:
            raise RepositoryAgentEvidenceInvalidError
        return tuple(citations)
