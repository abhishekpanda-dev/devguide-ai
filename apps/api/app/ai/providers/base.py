from dataclasses import dataclass
from typing import Protocol

from app.schemas.feature_location import FeatureLocationResult
from app.schemas.grounded_answer import EvidenceQuality, TokenUsage
from app.schemas.retrieval import RepositoryEvidence
from app.schemas.structure_evidence import StructureEvidence


@dataclass(frozen=True, slots=True)
class ProviderGroundedAnswerRequest:
    question: str
    evidence: tuple[RepositoryEvidence, ...]
    system_instructions: str
    user_prompt: str
    output_schema: dict[str, object]
    correlation_id: str | None
    maximum_output_tokens: int
    temperature: float
    structure_evidence: StructureEvidence | None = None
    feature_location: FeatureLocationResult | None = None


@dataclass(frozen=True, slots=True)
class ProviderGroundedAnswerResult:
    provider_name: str
    model_name: str
    answer_text: str
    cited_evidence_ids: tuple[str, ...]
    evidence_quality: EvidenceQuality
    insufficient_evidence: bool
    limitations: tuple[str, ...] = ()
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    provider_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderSuggestedFixRequest:
    evidence_id: str
    rule_id: str
    finding_explanation: str
    deterministic_recommendation: str
    evidence: RepositoryEvidence
    system_instructions: str
    user_prompt: str
    output_schema: dict[str, object]
    correlation_id: str | None
    maximum_output_tokens: int
    temperature: float


@dataclass(frozen=True, slots=True)
class ProviderSuggestedFixResult:
    provider_name: str
    model_name: str
    explanation: str
    probable_fix: str
    example_code: str | None
    cited_evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()


class LLMProvider(Protocol):
    async def generate_grounded_answer(
        self, request: ProviderGroundedAnswerRequest
    ) -> ProviderGroundedAnswerResult: ...


class SuggestedFixProvider(Protocol):
    async def generate_suggested_fix(
        self, request: ProviderSuggestedFixRequest
    ) -> ProviderSuggestedFixResult: ...
