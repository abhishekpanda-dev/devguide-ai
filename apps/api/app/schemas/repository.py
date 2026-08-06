from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

from app.models.enums import RepositorySourceType, RepositoryStatus

NonEmptyName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class RepositoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: RepositorySourceType = RepositorySourceType.GITHUB_PUBLIC
    source_url: HttpUrl
    normalized_url: HttpUrl
    owner: NonEmptyName
    name: NonEmptyName
    default_branch: str | None = Field(default=None, max_length=255)
    latest_commit_sha: str | None = Field(default=None, max_length=64)
    status: RepositoryStatus = RepositoryStatus.PENDING


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    source_type: RepositorySourceType
    source_url: str
    normalized_url: str
    owner: str
    name: str
    default_branch: str | None
    latest_commit_sha: str | None
    status: RepositoryStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
