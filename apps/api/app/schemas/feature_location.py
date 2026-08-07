from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


def _safe_path(value: str) -> str:
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


class FeatureFileRole(StrEnum):
    UI = "UI"
    API_ROUTE = "API route"
    SERVICE = "service"
    REPOSITORY = "repository/data access"
    MODEL = "model/schema"
    CONFIGURATION = "configuration"
    WORKER = "worker/job"
    TEST = "test"
    ENTRY_POINT = "entry point"
    UNKNOWN = "unknown"


class ImpactKind(StrEnum):
    DIRECT = "direct_static"
    INDIRECT = "probable_indirect"
    UNKNOWN = "unknown_dynamic"


class FeatureFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    repository_file_id: UUID
    path: str
    role: FeatureFileRole
    role_inferred: bool = True
    confidence: float = Field(ge=0, le=1)
    reason: str
    source_url: AnyHttpUrl
    evidence: tuple[str, ...] = Field(default=(), max_length=5)
    impact_kind: ImpactKind | None = None

    _validate_path = field_validator("path")(_safe_path)


class ImpactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    direct_dependencies: tuple[FeatureFile, ...] = ()
    direct_dependents: tuple[FeatureFile, ...] = ()
    probable_indirect: tuple[FeatureFile, ...] = ()
    probable_entry_points: tuple[FeatureFile, ...] = ()
    related_findings: tuple[str, ...] = ()
    related_quality_candidates: tuple[str, ...] = ()
    unknown_dynamic_impact: str


class ChangePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    start_here: tuple[str, ...]
    inspect_files: tuple[str, ...]
    likely_code_path: tuple[str, ...]
    potentially_affected_files: tuple[str, ...]
    tests_to_review: tuple[str, ...]
    risks_and_limitations: tuple[str, ...]


class FeatureLocationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    feature_location_used: bool = True
    intent: str
    feature_phrase: str
    likely_files: tuple[FeatureFile, ...]
    impact_summary: ImpactSummary
    related_tests: tuple[FeatureFile, ...]
    change_plan: ChangePlan
    limitations: tuple[str, ...]
