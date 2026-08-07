from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.repository_agent import RepositoryAgentRequest


class RepositoryQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    language_filters: tuple[str, ...] = Field(default=(), max_length=20)
    path_prefix: str | None = Field(default=None, max_length=2048)
    retrieval_limit: int = Field(default=10, ge=1, le=100)
    retrieval_minimum_score: float = Field(default=1.0, ge=0, le=110)
    maximum_citations: int = Field(default=10, ge=1, le=100)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must contain non-whitespace characters")
        return normalized

    @field_validator("language_filters")
    @classmethod
    def normalize_languages(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted({item.strip().lower() for item in value if item.strip()}))
        if len(normalized) != len(value):
            raise ValueError("language_filters must be non-empty and unique")
        return normalized

    @field_validator("path_prefix")
    @classmethod
    def validate_path_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().replace("\\", "/").rstrip("/")
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or PureWindowsPath(normalized).is_absolute()
            or ".." in path.parts
        ):
            raise ValueError("path_prefix must be repository-relative")
        return normalized

    def to_agent_request(
        self, *, analysis_job_id: UUID, correlation_id: str
    ) -> RepositoryAgentRequest:
        return RepositoryAgentRequest(
            analysis_job_id=analysis_job_id,
            question=self.question,
            languages=self.language_filters,
            path_prefix=self.path_prefix,
            retrieval_limit=self.retrieval_limit,
            retrieval_minimum_score=self.retrieval_minimum_score,
            maximum_citations=self.maximum_citations,
            correlation_id=correlation_id,
        )
