import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.providers import ClaudeProvider, ProviderGroundedAnswerRequest
from app.ai.providers.claude import MessagesClient
from app.core.exceptions import (
    AIProviderNotConfiguredError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseInvalidError,
)


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeMessages(MessagesClient):
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = iter(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.fake_messages = FakeMessages(outcomes)

    @property
    def messages(self) -> MessagesClient:
        return self.fake_messages


def request() -> ProviderGroundedAnswerRequest:
    return ProviderGroundedAnswerRequest(
        question="question",
        evidence=(),
        system_instructions="system",
        user_prompt="prompt",
        output_schema={"type": "object"},
        correlation_id=None,
        maximum_output_tokens=100,
        temperature=0,
    )


def response(text: str | None = None) -> Any:
    payload = text or json.dumps(
        {
            "answer": "Grounded.",
            "cited_evidence_ids": [],
            "evidence_quality": "low",
            "insufficient_evidence": False,
            "limitations": [],
        }
    )
    return SimpleNamespace(
        id="provider-id",
        content=[SimpleNamespace(text=payload)],
        usage=SimpleNamespace(input_tokens=11, output_tokens=7),
        stop_reason="end_turn",
    )


def provider(client: FakeClient, retries: int = 2, timeout: float = 1) -> ClaudeProvider:
    return ClaudeProvider(
        api_key="test-key",
        model="test-claude",
        timeout_seconds=timeout,
        retry_count=retries,
        client=client,
    )


def test_missing_key_fails_clearly() -> None:
    with pytest.raises(AIProviderNotConfiguredError) as caught:
        ClaudeProvider(api_key=None, model="model", timeout_seconds=1, retry_count=0)
    assert caught.value.code == "ai_provider_not_configured"


async def test_claude_structured_response_and_safe_metadata() -> None:
    client = FakeClient([response()])
    result = await provider(client).generate_grounded_answer(request())
    assert result.answer_text == "Grounded."
    assert result.provider_name == "claude"
    assert result.provider_request_id == "provider-id"
    assert client.fake_messages.calls[0]["output_config"]["format"]["type"] == "json_schema"


async def test_transient_failures_retry_then_succeed() -> None:
    client = FakeClient([ProviderError("secret transient detail", 503), response()])
    result = await provider(client).generate_grounded_answer(request())
    assert result.answer_text == "Grounded."
    assert len(client.fake_messages.calls) == 2


async def test_permanent_failure_is_not_retried_or_exposed() -> None:
    client = FakeClient([ProviderError("raw authentication secret", 401)])
    with pytest.raises(AIProviderUnavailableError) as caught:
        await provider(client).generate_grounded_answer(request())
    assert len(client.fake_messages.calls) == 1
    assert "authentication" not in caught.value.message
    assert "secret" not in caught.value.message


async def test_timeout_is_bounded_and_translated() -> None:
    class SlowMessages:
        calls = 0

        async def create(self, **kwargs: Any) -> Any:
            self.calls += 1
            raise TimeoutError("raw timeout")

    client = SimpleNamespace(messages=SlowMessages())
    with pytest.raises(AIProviderTimeoutError):
        await provider(client, retries=1).generate_grounded_answer(request())  # type: ignore[arg-type]
    assert client.messages.calls == 2


async def test_anthropic_sdk_timeout_is_retried_and_translated() -> None:
    class APITimeoutError(Exception):
        pass

    client = FakeClient([APITimeoutError("raw sdk timeout"), APITimeoutError("raw sdk timeout")])
    with pytest.raises(AIProviderTimeoutError) as caught:
        await provider(client, retries=1).generate_grounded_answer(request())
    assert len(client.fake_messages.calls) == 2
    assert "raw sdk timeout" not in caught.value.message


async def test_malformed_response_is_stable_error() -> None:
    client = FakeClient([response("not-json")])
    with pytest.raises(AIResponseInvalidError) as caught:
        await provider(client).generate_grounded_answer(request())
    assert caught.value.code == "ai_response_invalid"
