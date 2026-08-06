from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import AnalysisJobStatus, RepositorySourceType
from app.schemas import (
    AnalysisJobCreate,
    AnalysisStageCreate,
    RepositoryCreate,
    RepositoryRead,
)


def test_repository_create_validates_url_and_names() -> None:
    schema = RepositoryCreate(
        source_url="https://github.com/acme/project",
        normalized_url="https://github.com/acme/project",
        owner=" acme ",
        name=" project ",
    )
    assert schema.source_type is RepositorySourceType.GITHUB_PUBLIC
    assert schema.owner == "acme"
    assert schema.name == "project"

    with pytest.raises(ValidationError):
        RepositoryCreate(
            source_url="not-a-url",
            normalized_url="https://github.com/acme/project",
            owner="acme",
            name="project",
        )


def test_analysis_job_progress_schema_validation() -> None:
    with pytest.raises(ValidationError):
        AnalysisJobCreate(repository_id=uuid4(), pipeline_version="v1", progress_percent=101)
    with pytest.raises(ValidationError):
        AnalysisJobCreate(repository_id=uuid4(), pipeline_version="   ")


def test_analysis_stage_progress_and_attempt_schema_validation() -> None:
    with pytest.raises(ValidationError):
        AnalysisStageCreate(analysis_job_id=uuid4(), name="inventory", progress_percent=-1)
    with pytest.raises(ValidationError):
        AnalysisStageCreate(analysis_job_id=uuid4(), name="inventory", attempt=0)


def test_read_schema_uses_attributes_and_aware_datetimes() -> None:
    now = datetime.now(UTC)

    class RepositoryRecord:
        id = uuid4()
        source_type = RepositorySourceType.GITHUB_PUBLIC
        source_url = "https://github.com/acme/project"
        normalized_url = source_url
        owner = "acme"
        name = "project"
        default_branch = None
        latest_commit_sha = None
        status = "pending"
        created_at = now
        updated_at = now

    parsed = RepositoryRead.model_validate(RepositoryRecord())
    assert parsed.created_at.tzinfo is not None
    assert parsed.status.value == "pending"
    assert AnalysisJobStatus.QUEUED.value == "queued"
