from app.ai.prompts.grounded_answer import SYSTEM_INSTRUCTIONS, build_grounded_answer_prompt
from app.ai.providers.base import LLMProvider, ProviderGroundedAnswerRequest
from app.core.config import Settings
from app.core.exceptions import GroundedAnswerValidationError
from app.schemas.grounded_answer import (
    EvidenceQuality,
    GroundedAnswer,
    GroundedAnswerRequest,
    GroundedCitation,
)
from app.schemas.retrieval import RepositoryEvidence, SearchRepositoryResult
from app.schemas.structure_evidence import StructureEvidence


class GroundedAnswerService:
    def __init__(self, provider: LLMProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings

    async def answer(
        self,
        *,
        question: str,
        search_result: SearchRepositoryResult,
        correlation_id: str | None = None,
        maximum_citations: int = 10,
        structure_evidence: StructureEvidence | None = None,
    ) -> GroundedAnswer:
        request = GroundedAnswerRequest(
            analysis_job_id=search_result.analysis_job_id,
            question=question,
            evidence=search_result.evidence,
            maximum_citations=maximum_citations,
        )
        if not request.evidence:
            return GroundedAnswer(
                answer="The persisted repository evidence is insufficient to answer this question.",
                citations=(),
                evidence_quality=EvidenceQuality.INSUFFICIENT,
                insufficient_evidence=True,
                limitations=search_result.limitations
                or ("No validated repository evidence was available.",),
                provider="none",
                model="none",
            )
        evidence = self._bound_evidence(request.evidence)
        provider_request = ProviderGroundedAnswerRequest(
            question=request.question,
            evidence=evidence,
            structure_evidence=structure_evidence,
            system_instructions=SYSTEM_INSTRUCTIONS,
            user_prompt=build_grounded_answer_prompt(
                request.question, evidence, structure_evidence
            ),
            output_schema=self._output_schema(),
            correlation_id=correlation_id,
            maximum_output_tokens=self._settings.ai_maximum_output_tokens,
            temperature=self._settings.ai_temperature,
        )
        result = await self._provider.generate_grounded_answer(provider_request)
        citations = self._validate_citations(
            result.cited_evidence_ids, evidence, request.maximum_citations
        )
        if result.insufficient_evidence and citations:
            raise GroundedAnswerValidationError
        if not result.insufficient_evidence and not citations:
            raise GroundedAnswerValidationError
        if not result.answer_text.strip() and not result.insufficient_evidence:
            raise GroundedAnswerValidationError
        return GroundedAnswer(
            answer=result.answer_text,
            citations=citations,
            evidence_quality=result.evidence_quality,
            insufficient_evidence=result.insufficient_evidence,
            limitations=result.limitations,
            provider=result.provider_name,
            model=result.model_name,
            usage=result.usage,
            finish_reason=result.finish_reason,
            provider_request_id=result.provider_request_id,
        )

    def _bound_evidence(
        self, evidence: tuple[RepositoryEvidence, ...]
    ) -> tuple[RepositoryEvidence, ...]:
        bounded: list[RepositoryEvidence] = []
        remaining = self._settings.ai_maximum_evidence_characters
        for item in evidence[: self._settings.ai_maximum_evidence_items]:
            if remaining <= 0:
                break
            excerpt = item.excerpt[:remaining]
            bounded.append(item.model_copy(update={"excerpt": excerpt}))
            remaining -= len(excerpt)
        return tuple(bounded)

    @staticmethod
    def _validate_citations(
        cited_ids: tuple[str, ...],
        evidence: tuple[RepositoryEvidence, ...],
        maximum: int,
    ) -> tuple[GroundedCitation, ...]:
        available = {item.chunk_id: item for item in evidence}
        unique: list[GroundedCitation] = []
        seen: set[str] = set()
        for chunk_id in cited_ids:
            if chunk_id in seen:
                continue
            item = available.get(chunk_id)
            if item is None:
                raise GroundedAnswerValidationError
            seen.add(chunk_id)
            unique.append(
                GroundedCitation(
                    chunk_id=item.chunk_id,
                    path=item.path,
                    start_line=item.start_line,
                    end_line=item.end_line,
                    content_hash=item.content_hash,
                )
            )
        if len(unique) > maximum:
            raise GroundedAnswerValidationError
        return tuple(unique)

    @staticmethod
    def _output_schema() -> dict[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "answer",
                "cited_evidence_ids",
                "evidence_quality",
                "insufficient_evidence",
                "limitations",
            ],
            "properties": {
                "answer": {"type": "string"},
                "cited_evidence_ids": {"type": "array", "items": {"type": "string"}},
                "evidence_quality": {"enum": ["high", "moderate", "low", "insufficient"]},
                "insufficient_evidence": {"type": "boolean"},
                "limitations": {"type": "array", "items": {"type": "string"}},
            },
        }
