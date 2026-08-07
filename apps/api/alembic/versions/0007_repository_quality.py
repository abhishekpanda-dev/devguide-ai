"""Persist deterministic repository quality intelligence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_repository_quality"
down_revision: str | None = "0006_repository_structure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_quality_metadata",
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("category_scores", sa.JSON(), nullable=False),
        sa.Column("deductions", sa.JSON(), nullable=False),
        sa.Column("score_version", sa.String(100), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
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
            "overall_score >= 0 AND overall_score <= 100", name="quality_score_range"
        ),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("analysis_job_id"),
    )
    op.create_table(
        "unused_code_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("symbol_name", sa.String(512), nullable=False),
        sa.Column("symbol_kind", sa.String(50), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(2000), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.CheckConstraint("start_line >= 1 AND end_line >= start_line", name="unused_line_range"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="unused_confidence_range"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id",
            "repository_file_id",
            "symbol_name",
            "start_line",
            name="uq_unused_candidate",
        ),
    )
    op.create_table(
        "duplicate_code_groups",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(2000), nullable=False),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", "analysis_job_id"),
    )
    op.create_table(
        "duplicate_code_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.String(64), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id",
            "group_id",
            "repository_file_id",
            "start_line",
            name="uq_duplicate_member",
        ),
    )
    for table, columns in (
        ("unused_code_candidates", ("analysis_job_id", "path", "language")),
        ("duplicate_code_groups", ("analysis_job_id",)),
        ("duplicate_code_members", ("analysis_job_id", "path", "language")),
    ):
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("duplicate_code_members")
    op.drop_table("duplicate_code_groups")
    op.drop_table("unused_code_candidates")
    op.drop_table("analysis_quality_metadata")
