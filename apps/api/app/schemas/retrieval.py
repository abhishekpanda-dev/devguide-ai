from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MatchedChannel(StrEnum):
    EXACT_PATH = "exact_path"
    PARTIAL_PATH = "partial_path"
    EXACT_PHRASE = "exact_phrase"
    TOKEN_OVERLAP = "token_overlap"
    SYMBOL = "symbol"
    LANGUAGE = "language"
    PATH_PREFIX = "path_prefix"


class SearchRepositoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_job_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    languages: tuple[str, ...] = Field(default=(), max_length=20)
    path_prefix: str | None = Field(default=None, max_length=2048)
    limit: int = Field(default=10, ge=1, le=100)
    minimum_score: float = Field(default=1.0, ge=0, le=110)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must contain non-whitespace characters")
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
        return f"{normalized}/"


class RepositoryEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_file_id: UUID
    chunk_id: str
    path: str
    language: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    excerpt: str
    score: float = Field(ge=0)
    matched_channels: tuple[MatchedChannel, ...]
    content_hash: str
    commit_sha: str
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_citation_shape(self) -> "RepositoryEvidence":
        path = PurePosixPath(self.path)
        if (
            not self.path
            or "\\" in self.path
            or path.is_absolute()
            or PureWindowsPath(self.path).is_absolute()
            or ".." in path.parts
        ):
            raise ValueError("path must be repository-relative POSIX form")
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class SearchCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channels: tuple[MatchedChannel, ...]
    candidate_files: int = Field(ge=0)
    candidate_chunks: int = Field(ge=0)
    strong_matches: int = Field(ge=0)


class SearchRepositoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_job_id: UUID
    query: str
    evidence: tuple[RepositoryEvidence, ...]
    total_candidates: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    coverage: SearchCoverage
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_counts(self) -> "SearchRepositoryResult":
        if self.returned_count != len(self.evidence):
            raise ValueError("returned_count must match evidence length")
        if self.returned_count > self.total_candidates:
            raise ValueError("returned_count cannot exceed total_candidates")
        return self
