from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DEVGUIDE_",
        case_sensitive=False,
        extra="ignore",
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

    @field_validator("database_url")
    @classmethod
    def require_asyncpg(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+asyncpg":
            raise ValueError("database_url must use the postgresql+asyncpg scheme")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
