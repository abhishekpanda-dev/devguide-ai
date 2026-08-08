from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_validation_rejects_invalid_pool_size() -> None:
    with pytest.raises(ValidationError):
        Settings(database_pool_size=0)


def test_settings_validation_requires_async_postgresql_driver() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://devguide:devguide@localhost/devguide",
        )


def test_safe_defaults_use_postgresql() -> None:
    settings = Settings()

    assert settings.app_name == "devguide-api"
    assert settings.database_url.scheme == "postgresql+asyncpg"
    assert settings.analysis_pipeline_version == "1"
    assert settings.clone_depth == 1
    assert settings.temporary_workspace_root.is_absolute()


def test_ingestion_settings_validate_safe_boundaries() -> None:
    with pytest.raises(ValidationError):
        Settings(clone_depth=2)

    with pytest.raises(ValidationError):
        Settings(temporary_workspace_root=Path("relative/workspaces"))


def test_ai_settings_have_safe_bounded_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEVGUIDE_AI_PROVIDER", raising=False)

    settings = Settings(environment="test", _env_file=None)

    assert settings.ai_provider_name == "claude"
    assert settings.anthropic_api_key is None
    assert settings.ai_temperature == 0
    assert settings.ai_retry_count == 2

    with pytest.raises(ValidationError):
        Settings(ai_maximum_evidence_items=0)


def test_public_ai_provider_environment_name_is_supported() -> None:
    settings = Settings.model_validate(
        {
            "DEVGUIDE_AI_PROVIDER": "mock",
            "environment": "test",
        },
    )

    assert settings.ai_provider_name == "mock"


def test_live_claude_settings_are_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVGUIDE_AI_PROVIDER", "claude")
    monkeypatch.setenv("DEVGUIDE_ANTHROPIC_API_KEY", "secret-test-key")
    monkeypatch.setenv("DEVGUIDE_CLAUDE_MODEL", "test-claude-model")
    monkeypatch.setenv("DEVGUIDE_AI_REQUEST_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("DEVGUIDE_AI_MAXIMUM_OUTPUT_TOKENS", "2048")
    monkeypatch.setenv("DEVGUIDE_AI_TEMPERATURE", "0.2")
    monkeypatch.setenv("DEVGUIDE_AI_RETRY_COUNT", "1")

    settings = Settings(_env_file=None)

    assert settings.ai_provider_name == "claude"
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "secret-test-key"
    assert "secret-test-key" not in repr(settings)
    assert settings.claude_model == "test-claude-model"
    assert settings.ai_request_timeout_seconds == 12.5
    assert settings.ai_maximum_output_tokens == 2048
    assert settings.ai_temperature == 0.2
    assert settings.ai_retry_count == 1


def test_blank_anthropic_key_is_treated_as_missing() -> None:
    assert Settings(anthropic_api_key="").anthropic_api_key is None
