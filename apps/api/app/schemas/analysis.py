from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import AnalysisJobStatus, AnalysisStageStatus

NonEmptyValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnalysisJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_id: UUID
    status: AnalysisJobStatus = AnalysisJobStatus.QUEUED
    current_stage: str | None = Field(default=None, max_length=255)
    progress_percent: int = Field(default=0, ge=0, le=100)
    pipeline_version: NonEmptyValue = Field(max_length=100)


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    repository_id: UUID
    status: AnalysisJobStatus
    current_stage: str | None
    progress_percent: int = Field(ge=0, le=100)
    pipeline_version: str
    error_code: str | None
    error_message: str | None
    started_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AnalysisStageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_job_id: UUID
    name: NonEmptyValue = Field(max_length=255)
    status: AnalysisStageStatus = AnalysisStageStatus.PENDING
    attempt: int = Field(default=1, ge=1)
    progress_percent: int = Field(default=0, ge=0, le=100)


class AnalysisStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    analysis_job_id: UUID
    name: str
    status: AnalysisStageStatus
    attempt: int = Field(ge=1)
    progress_percent: int = Field(ge=0, le=100)
    error_code: str | None
    error_message: str | None
    started_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    heartbeat_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
