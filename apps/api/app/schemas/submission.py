from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import AnalysisJobRead
from app.schemas.repository import RepositoryRead


class RepositorySubmissionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"source_url": "https://github.com/owner/repository"}]},
    )

    source_url: str = Field(min_length=1, max_length=2048)


class RepositorySubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: RepositoryRead
    analysis_job: AnalysisJobRead


class RepositoryAnalysisListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AnalysisJobRead]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
