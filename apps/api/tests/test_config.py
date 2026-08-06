from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_validation_rejects_invalid_pool_size() -> None:
    with pytest.raises(ValidationError):
        Settings(database_pool_size=0)


def test_settings_validation_requires_async_postgresql_driver() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://devguide:devguide@localhost/devguide")


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
