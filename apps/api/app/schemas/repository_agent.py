from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.grounded_answer import EvidenceQuality


class RepositoryAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_job_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    languages: tuple[str, ...] = Field(default=(), max_length=20)
    path_prefix: str | None = Field(default=None, max_length=2048)
    retrieval_limit: int = Field(default=10, ge=1, le=100)
    retrieval_minimum_score: float = Field(default=1.0, ge=0, le=110)
    maximum_citations: int = Field(default=10, ge=1, le=100)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must contain non-whitespace characters")
        return normalized

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted({item.strip().lower() for item in value if item.strip()}))
        if len(normalized) != len(value):
            raise ValueError("languages must be non-empty and unique")
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

    @field_validator("correlation_id")
    @classmethod
    def normalize_correlation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or any(character in normalized for character in "\r\n\x00"):
            raise ValueError("correlation_id contains invalid characters")
        return normalized


class RepositoryAgentCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    repository_file_id: UUID
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content_hash: str

    @model_validator(mode="after")
    def validate_citation(self) -> "RepositoryAgentCitation":
        path = PurePosixPath(self.path)
        if (
            not self.path
            or "\\" in self.path
            or path.is_absolute()
            or PureWindowsPath(self.path).is_absolute()
            or ".." in path.parts
        ):
            raise ValueError("citation path must be repository-relative POSIX form")
        if self.end_line < self.start_line:
            raise ValueError("citation line range is invalid")
        return self


class RepositoryAgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_job_id: UUID
    question: str
    answer: str
    citations: tuple[RepositoryAgentCitation, ...]
    insufficient_evidence: bool
    evidence_quality: EvidenceQuality
    retrieved_evidence_count: int = Field(ge=0)
    provider: str | None
    model: str | None
    limitations: tuple[str, ...] = ()
    correlation_id: str | None = None
    structure_evidence_used: bool = False

    @model_validator(mode="after")
    def validate_response(self) -> "RepositoryAgentResponse":
        if self.insufficient_evidence and self.citations:
            raise ValueError("insufficient-evidence responses cannot contain citations")
        if not self.insufficient_evidence and not self.answer.strip():
            raise ValueError("grounded answer must not be empty")
        return self
