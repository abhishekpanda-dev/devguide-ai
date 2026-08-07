from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import FindingCategory, FindingSeverity


class CodeFindingRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    rule_id: str
    severity: FindingSeverity
    category: FindingCategory
    title: str
    explanation: str
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    evidence_excerpt: str = Field(max_length=500)
    deterministic_recommendation: str
    confidence: float = Field(ge=0, le=1)
    content_hash: str
    commit_sha: str
    source_url: AnyHttpUrl

    @field_validator("path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or path.is_absolute()
            or PureWindowsPath(value).is_absolute()
            or ".." in path.parts
        ):
            raise ValueError("unsafe finding path")
        return value

    @model_validator(mode="after")
    def lines(self) -> "CodeFindingRead":
        if self.end_line < self.start_line:
            raise ValueError("invalid finding lines")
        return self


class CodeFindingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_job_id: UUID
    total_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    findings: list[CodeFindingRead]
    limitations: list[str]
    severity_counts: dict[FindingSeverity, int]


class SuggestedFixCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content_hash: str
    source_url: AnyHttpUrl


class SuggestedFixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_job_id: UUID
    finding_id: UUID
    rule_id: str
    explanation: str
    probable_fix: str
    example_code: str | None
    citations: list[SuggestedFixCitation]
    provider: str
    model: str
    limitations: list[str]
    correlation_id: str | None
