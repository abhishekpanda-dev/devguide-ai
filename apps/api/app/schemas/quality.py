from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


def safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or ".." in path.parts
    ):
        raise ValueError("path must be repository-relative")
    return value


class ScoreDeductionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    signal_type: str
    count: int = Field(ge=0)
    points_deducted: int = Field(ge=0)
    explanation: str


class UnusedCandidateRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    symbol_name: str
    symbol_kind: str
    path: str
    language: str
    start_line: int
    end_line: int
    reason: str
    confidence: float
    recommendation: str
    excerpt: str
    source_url: AnyHttpUrl
    _path = field_validator("path")(safe_path)


class DuplicateMemberRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    language: str
    start_line: int
    end_line: int
    excerpt: str
    source_url: AnyHttpUrl
    _path = field_validator("path")(safe_path)


class DuplicateGroupRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: str
    match_type: str = "exact_normalized"
    confidence: float
    recommendation: str
    members: list[DuplicateMemberRead]


class QualityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_job_id: UUID
    overall_score: int = Field(ge=0, le=100)
    category_scores: dict[str, int]
    score_breakdown: list[ScoreDeductionRead]
    unused_code_candidates: list[UnusedCandidateRead]
    duplicate_code_groups: list[DuplicateGroupRead]
    summary: dict[str, int]
    limitations: list[str]
    score_version: str
