from enum import StrEnum

from app.ai.providers.base import (
    ProviderGroundedAnswerRequest,
    ProviderGroundedAnswerResult,
)
from app.core.exceptions import (
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseInvalidError,
)
from app.schemas.grounded_answer import EvidenceQuality, TokenUsage


class MockProviderMode(StrEnum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MALFORMED = "malformed"
    FAILURE = "failure"


class MockLLMProvider:
    def __init__(self, mode: MockProviderMode = MockProviderMode.SUCCESS) -> None:
        self.mode = mode
        self.requests: list[ProviderGroundedAnswerRequest] = []

    async def generate_grounded_answer(
        self, request: ProviderGroundedAnswerRequest
    ) -> ProviderGroundedAnswerResult:
        self.requests.append(request)
        if self.mode is MockProviderMode.TIMEOUT:
            raise AIProviderTimeoutError
        if self.mode is MockProviderMode.MALFORMED:
            raise AIResponseInvalidError
        if self.mode is MockProviderMode.FAILURE:
            raise AIProviderUnavailableError
        cited = (request.evidence[0].chunk_id,) if request.evidence else ()
        return ProviderGroundedAnswerResult(
            provider_name="mock",
            model_name="mock-grounded-v1",
            answer_text="The supplied evidence supports this deterministic mock answer.",
            cited_evidence_ids=cited,
            evidence_quality=EvidenceQuality.HIGH if cited else EvidenceQuality.INSUFFICIENT,
            insufficient_evidence=not cited,
            limitations=(),
            usage=TokenUsage(input_tokens=10, output_tokens=8),
            finish_reason="end_turn",
            provider_request_id="mock-request-1",
        )
