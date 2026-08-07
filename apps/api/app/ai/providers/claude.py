import asyncio
import importlib
import json
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from app.ai.providers.base import (
    ProviderGroundedAnswerRequest,
    ProviderGroundedAnswerResult,
)
from app.core.exceptions import (
    AIProviderNotConfiguredError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseInvalidError,
)
from app.schemas.grounded_answer import EvidenceQuality, TokenUsage


class MessagesClient(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class ClaudeClient(Protocol):
    @property
    def messages(self) -> MessagesClient: ...


class _StructuredClaudeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    cited_evidence_ids: tuple[str, ...]
    evidence_quality: EvidenceQuality
    insufficient_evidence: bool
    limitations: tuple[str, ...] = ()


class ClaudeProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: float,
        retry_count: int,
        client: ClaudeClient | None = None,
    ) -> None:
        if not api_key:
            raise AIProviderNotConfiguredError
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._retry_count = retry_count
        self._client = client or self._create_client(api_key, timeout_seconds)

    @staticmethod
    def _create_client(api_key: str, timeout_seconds: float) -> ClaudeClient:
        try:
            module = importlib.import_module("anthropic")
            client: ClaudeClient = module.AsyncAnthropic(
                api_key=api_key, timeout=timeout_seconds, max_retries=0
            )
            return client
        except (ImportError, AttributeError) as exc:
            raise AIProviderNotConfiguredError from exc

    async def generate_grounded_answer(
        self, request: ProviderGroundedAnswerRequest
    ) -> ProviderGroundedAnswerResult:
        response: Any = None
        for attempt in range(self._retry_count + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.messages.create(
                        model=self._model,
                        max_tokens=request.maximum_output_tokens,
                        temperature=request.temperature,
                        system=request.system_instructions,
                        messages=[{"role": "user", "content": request.user_prompt}],
                        output_config={
                            "format": {"type": "json_schema", "schema": request.output_schema}
                        },
                        metadata={"user_id": request.correlation_id}
                        if request.correlation_id
                        else None,
                    ),
                    timeout=self._timeout_seconds,
                )
                break
            except TimeoutError as exc:
                if attempt == self._retry_count:
                    raise AIProviderTimeoutError from exc
            except Exception as exc:
                if self._is_timeout(exc):
                    if attempt == self._retry_count:
                        raise AIProviderTimeoutError from exc
                elif not self._is_transient(exc) or attempt == self._retry_count:
                    raise AIProviderUnavailableError from exc
        if response is None:
            raise AIProviderUnavailableError
        return self._parse_response(response)

    def _parse_response(self, response: Any) -> ProviderGroundedAnswerResult:
        try:
            text = response.content[0].text
            structured = _StructuredClaudeResponse.model_validate(json.loads(text))
            usage = TokenUsage(
                input_tokens=getattr(response.usage, "input_tokens", None),
                output_tokens=getattr(response.usage, "output_tokens", None),
            )
        except (
            AttributeError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise AIResponseInvalidError from exc
        return ProviderGroundedAnswerResult(
            provider_name="claude",
            model_name=self._model,
            answer_text=structured.answer,
            cited_evidence_ids=structured.cited_evidence_ids,
            evidence_quality=structured.evidence_quality,
            insufficient_evidence=structured.insufficient_evidence,
            limitations=structured.limitations,
            usage=usage,
            finish_reason=getattr(response, "stop_reason", None),
            provider_request_id=getattr(response, "id", None),
        )

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        return (
            exc.__class__.__name__
            in {
                "APIConnectionError",
                "InternalServerError",
                "RateLimitError",
            }
            or status_code in {408, 409, 429}
            or (isinstance(status_code, int) and 500 <= status_code < 600)
        )

    @staticmethod
    def _is_timeout(exc: Exception) -> bool:
        return isinstance(exc, TimeoutError) or exc.__class__.__name__ == "APITimeoutError"
