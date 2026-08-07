from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


def safe_repository_path(value: str) -> str:
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


class StructureFileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_file_id: UUID
    path: str
    language: str
    classification: str
    line_count: int = Field(ge=0)
    content_hash: str
    commit_sha: str
    is_entry_point: bool
    entry_point_reason: str | None
    entry_point_confidence: float = Field(ge=0, le=1)
    inbound_dependency_count: int = Field(ge=0)
    outbound_dependency_count: int = Field(ge=0)
    total_dependency_count: int = Field(ge=0)

    _safe_path = field_validator("path")(safe_repository_path)


class StructureEdgeRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    source_repository_file_id: UUID
    target_repository_file_id: UUID
    relationship_type: str
    module_name: str
    source_path: str
    target_path: str
    source_line: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)
    source_url: AnyHttpUrl

    _safe_paths = field_validator("source_path", "target_path")(safe_repository_path)


class StructureRepositoryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    owner: str
    name: str
    commit_sha: str


class StructureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_count: int
    directory_count: int
    language_counts: dict[str, int]
    edge_count: int
    entry_point_count: int
    highest_inbound_files: list[StructureFileRead]
    highest_outbound_files: list[StructureFileRead]
    most_connected_files: list[StructureFileRead]


class StructureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_job_id: UUID
    repository: StructureRepositoryRead
    files: list[StructureFileRead]
    dependency_edges: list[StructureEdgeRead]
    entry_points: list[StructureFileRead]
    summary: StructureSummary
    limitations: list[str]
