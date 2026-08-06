"""Create repository analysis persistence tables.

Revision ID: 0001_repository_analysis
Revises:
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_repository_analysis"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

repository_source_type = postgresql.ENUM(
    "github_public", name="repository_source_type", create_type=False
)
repository_status = postgresql.ENUM(
    "pending", "ready", "failed", "archived", name="repository_status", create_type=False
)
analysis_job_status = postgresql.ENUM(
    "queued",
    "running",
    "partial",
    "completed",
    "failed",
    "cancelled",
    name="analysis_job_status",
    create_type=False,
)
analysis_stage_status = postgresql.ENUM(
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    name="analysis_stage_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    repository_source_type.create(bind, checkfirst=False)
    repository_status.create(bind, checkfirst=False)
    analysis_job_status.create(bind, checkfirst=False)
    analysis_stage_status.create(bind, checkfirst=False)

    op.create_table(
        "repositories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", repository_source_type, nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("latest_commit_sha", sa.String(length=64), nullable=True),
        sa.Column("status", repository_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(owner)) > 0", name="owner_not_empty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.PrimaryKeyConstraint("id", name="pk_repositories"),
        sa.UniqueConstraint("normalized_url", name="uq_repositories_normalized_url"),
    )
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("status", analysis_job_status, nullable=False),
        sa.Column("current_stage", sa.String(length=255), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=100), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="progress_percent_range",
        ),
        sa.CheckConstraint(
            "length(trim(pipeline_version)) > 0",
            name="pipeline_version_not_empty",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_analysis_jobs_repository_id_repositories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_jobs"),
    )
    op.create_index(
        "ix_analysis_jobs_repository_id", "analysis_jobs", ["repository_id"], unique=False
    )
    op.create_table(
        "analysis_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", analysis_stage_status, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempt >= 1", name="attempt_at_least_one"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="progress_percent_range",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_job_id"],
            ["analysis_jobs.id"],
            name="fk_analysis_stages_analysis_job_id_analysis_jobs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_stages"),
    )
    op.create_index(
        "ix_analysis_stages_analysis_job_id",
        "analysis_stages",
        ["analysis_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_stages_analysis_job_id", table_name="analysis_stages")
    op.drop_table("analysis_stages")
    op.drop_index("ix_analysis_jobs_repository_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_table("repositories")

    bind = op.get_bind()
    analysis_stage_status.drop(bind, checkfirst=False)
    analysis_job_status.drop(bind, checkfirst=False)
    repository_status.drop(bind, checkfirst=False)
    repository_source_type.drop(bind, checkfirst=False)
