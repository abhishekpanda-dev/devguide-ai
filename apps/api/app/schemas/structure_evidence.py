from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class StructureFileFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    repository_file_id: UUID
    path: str
    language: str
    classification: str
    inbound_count: int = Field(ge=0)
    outbound_count: int = Field(ge=0)
    is_probable_entry_point: bool = False
    entry_point_reason: str | None = None
    entry_point_confidence: float = Field(default=0, ge=0, le=1)

    @field_validator("path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        return safe_path(value)


class StructureEdgeFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_path: str
    target_path: str
    relationship_type: str
    module_name: str
    source_line: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)

    _safe_paths = field_validator("source_path", "target_path")(safe_path)


class StructureEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    analysis_job_id: UUID
    language_counts: dict[str, int] = Field(default_factory=dict)
    directory_counts: dict[str, int] = Field(default_factory=dict)
    probable_entry_points: tuple[StructureFileFact, ...] = ()
    highest_inbound: tuple[StructureFileFact, ...] = ()
    highest_outbound: tuple[StructureFileFact, ...] = ()
    most_connected: tuple[StructureFileFact, ...] = ()
    dependency_edges: tuple[StructureEdgeFact, ...] = ()
    limitations: tuple[str, ...] = ()
