from typing import cast

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Table,
    UniqueConstraint,
    inspect,
)

from app.models import (
    AnalysisJob,
    AnalysisJobStatus,
    AnalysisStage,
    AnalysisStageStatus,
    Repository,
    RepositorySourceType,
    RepositoryStatus,
)


def test_enum_values_are_stable() -> None:
    assert [item.value for item in RepositorySourceType] == ["github_public"]
    assert [item.value for item in RepositoryStatus] == ["pending", "ready", "failed", "archived"]
    assert [item.value for item in AnalysisJobStatus] == [
        "queued",
        "running",
        "partial",
        "completed",
        "failed",
        "cancelled",
    ]
    assert [item.value for item in AnalysisStageStatus] == [
        "pending",
        "running",
        "completed",
        "failed",
        "skipped",
    ]


def test_model_metadata_contains_required_constraints_and_indexes() -> None:
    repository_table = cast(Table, Repository.__table__)
    job_table = cast(Table, AnalysisJob.__table__)
    stage_table = cast(Table, AnalysisStage.__table__)
    repository_constraints = repository_table.constraints
    assert any(
        isinstance(item, UniqueConstraint) and item.name == "uq_repositories_normalized_url"
        for item in repository_constraints
    )
    assert {
        "ck_analysis_jobs_pipeline_version_not_empty",
        "ck_analysis_jobs_progress_percent_range",
    }.issubset({item.name for item in job_table.constraints if isinstance(item, CheckConstraint)})
    assert {
        "ck_analysis_stages_attempt_at_least_one",
        "ck_analysis_stages_name_not_empty",
        "ck_analysis_stages_progress_percent_range",
    }.issubset({item.name for item in stage_table.constraints if isinstance(item, CheckConstraint)})
    assert any(
        isinstance(item, UniqueConstraint) and item.name == "uq_analysis_stages_job_name"
        for item in stage_table.constraints
    )
    assert job_table.c.repository_id.index is True
    assert stage_table.c.analysis_job_id.index is True


def test_timestamps_are_timezone_aware_database_types() -> None:
    for model in (Repository, AnalysisJob, AnalysisStage):
        for column_name in ("created_at", "updated_at"):
            column_type = model.__table__.c[column_name].type
            assert isinstance(column_type, DateTime)
            assert column_type.timezone is True


def test_relationships_are_bidirectional_without_delete_cascade() -> None:
    repository_relationship = inspect(Repository).relationships.analysis_jobs
    job_repository_relationship = inspect(AnalysisJob).relationships.repository
    stage_relationship = inspect(AnalysisJob).relationships.stages
    stage_job_relationship = inspect(AnalysisStage).relationships.analysis_job

    assert repository_relationship.back_populates == "repository"
    assert job_repository_relationship.back_populates == "analysis_jobs"
    assert stage_relationship.back_populates == "analysis_job"
    assert stage_job_relationship.back_populates == "stages"
    assert "delete" not in repository_relationship.cascade
    assert "delete" not in stage_relationship.cascade


def test_foreign_keys_are_restrictive() -> None:
    job_table = cast(Table, AnalysisJob.__table__)
    stage_table = cast(Table, AnalysisStage.__table__)
    job_fk = next(item for item in job_table.constraints if isinstance(item, ForeignKeyConstraint))
    stage_fk = next(
        item for item in stage_table.constraints if isinstance(item, ForeignKeyConstraint)
    )
    assert job_fk.ondelete == "RESTRICT"
    assert stage_fk.ondelete == "RESTRICT"
