import pytest

from app.ai.agents.factory import build_llm_provider
from app.ai.providers import ClaudeProvider, MockLLMProvider
from app.ai.providers.claude import MessagesClient
from app.core.config import Settings
from app.core.exceptions import AIProviderNotConfiguredError


class OfflineClient:
    @property
    def messages(self) -> MessagesClient:
        raise AssertionError("provider construction must not make a network request")


def test_claude_provider_is_constructed_from_settings_without_network() -> None:
    client = OfflineClient()
    settings = Settings(
        environment="local",
        ai_provider_name="claude",
        anthropic_api_key="test-key",
        claude_model="configured-model",
        ai_request_timeout_seconds=17,
        ai_retry_count=1,
    )

    provider = build_llm_provider(settings, claude_client=client)

    assert isinstance(provider, ClaudeProvider)
    assert provider._model == "configured-model"
    assert provider._timeout_seconds == 17
    assert provider._retry_count == 1
    assert provider._client is client


def test_claude_selection_without_key_is_not_configured() -> None:
    with pytest.raises(AIProviderNotConfiguredError) as caught:
        build_llm_provider(Settings(environment="local", ai_provider_name="claude"))
    assert caught.value.code == "ai_provider_not_configured"


def test_mock_selection_is_offline_and_deterministic() -> None:
    first = build_llm_provider(Settings(environment="test", ai_provider_name="mock"))
    second = build_llm_provider(Settings(environment="test", ai_provider_name="mock"))
    assert isinstance(first, MockLLMProvider)
    assert isinstance(second, MockLLMProvider)
    assert first.mode == second.mode


def test_mock_is_rejected_outside_local_and_test() -> None:
    with pytest.raises(AIProviderNotConfiguredError):
        build_llm_provider(Settings(environment="production", ai_provider_name="mock"))
