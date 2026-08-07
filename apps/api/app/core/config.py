from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Literal

from pydantic import AliasChoices, AnyUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DEVGUIDE_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "devguide-api"
    app_version: str = Field(default="0.1.0", min_length=1)
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://devguide:devguide@localhost:5432/devguide"
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    analysis_pipeline_version: str = Field(default="1", min_length=1, max_length=100)
    clone_timeout_seconds: float = Field(default=60.0, gt=0, le=900)
    maximum_repository_size_mb: int = Field(default=100, ge=1, le=1024)
    maximum_repository_file_count: int = Field(default=20_000, ge=1, le=1_000_000)
    maximum_individual_file_size_mb: int = Field(default=5, ge=1, le=100)
    temporary_workspace_root: Path = Path(gettempdir()) / "devguide-workspaces"
    git_executable: str = Field(default="git", min_length=1, max_length=1024)
    clone_depth: Literal[1] = 1
    redis_url: AnyUrl = AnyUrl("redis://localhost:6379/0")
    queue_name: str = Field(default="devguide-analysis", min_length=1, max_length=100)
    worker_concurrency: int = Field(default=4, ge=1, le=100)
    worker_job_timeout_seconds: int = Field(default=300, ge=1, le=3600)
    worker_retry_count: int = Field(default=3, ge=0, le=10)
    worker_retry_delay_seconds: int = Field(default=5, ge=0, le=300)
    worker_heartbeat_interval_seconds: int = Field(default=15, ge=1, le=300)
    ai_provider_name: Literal["claude", "mock"] = Field(
        default="claude",
        validation_alias=AliasChoices("DEVGUIDE_AI_PROVIDER", "DEVGUIDE_AI_PROVIDER_NAME"),
    )
    claude_model: str = Field(default="claude-sonnet-4-5", min_length=1, max_length=200)
    anthropic_api_key: str | None = Field(default=None, min_length=1)
    ai_request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    ai_maximum_output_tokens: int = Field(default=1024, ge=1, le=8192)
    ai_maximum_evidence_items: int = Field(default=10, ge=1, le=100)
    ai_maximum_evidence_characters: int = Field(default=30_000, ge=1, le=200_000)
    ai_retry_count: int = Field(default=2, ge=0, le=5)
    ai_temperature: float = Field(default=0.0, ge=0, le=1)

    @field_validator("database_url")
    @classmethod
    def require_asyncpg(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+asyncpg":
            raise ValueError("database_url must use the postgresql+asyncpg scheme")
        return value

    @field_validator("temporary_workspace_root")
    @classmethod
    def require_absolute_workspace_root(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("temporary_workspace_root must be absolute")
        return value

    @field_validator("git_executable")
    @classmethod
    def reject_invalid_git_executable(cls, value: str) -> str:
        if "\x00" in value or "\r" in value or "\n" in value:
            raise ValueError("git_executable contains invalid characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
