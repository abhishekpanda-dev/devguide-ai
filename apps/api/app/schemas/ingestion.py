from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryIngestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_id: UUID
    analysis_job_id: UUID
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")
    default_branch: str | None
    scanned_file_count: int = Field(ge=0)
    scanned_size_bytes: int = Field(ge=0)
    skipped_directory_count: int = Field(ge=0)
    completed_stage: str
    limitations: list[str]
