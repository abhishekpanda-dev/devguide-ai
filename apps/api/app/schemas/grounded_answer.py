from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.retrieval import RepositoryEvidence


class EvidenceQuality(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class GroundedAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_job_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    evidence: tuple[RepositoryEvidence, ...]
    maximum_citations: int = Field(default=10, ge=1, le=100)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must contain non-whitespace characters")
        return normalized


class GroundedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content_hash: str

    @model_validator(mode="after")
    def validate_range(self) -> "GroundedCitation":
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


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: tuple[GroundedCitation, ...]
    evidence_quality: EvidenceQuality
    insufficient_evidence: bool
    limitations: tuple[str, ...] = ()
    provider: str
    model: str
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    provider_request_id: str | None = None

    @model_validator(mode="after")
    def validate_answer_state(self) -> "GroundedAnswer":
        if not self.answer.strip() and not self.insufficient_evidence:
            raise ValueError("answer must not be empty when evidence is sufficient")
        if self.insufficient_evidence and self.citations:
            raise ValueError("insufficient-evidence answers cannot contain citations")
        return self
