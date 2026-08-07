"""Persist deterministic code findings."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_code_findings"
down_revision: str | None = "0004_analysis_parse_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
finding_severity = postgresql.ENUM(
    "info", "warning", "high", name="finding_severity", create_type=False
)
finding_category = postgresql.ENUM(
    "maintainability",
    "reliability",
    "security",
    name="finding_category",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    finding_severity.create(bind, checkfirst=True)
    finding_category.create(bind, checkfirst=True)
    op.create_table(
        "analysis_findings_metadata",
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("analysis_job_id"),
    )
    op.create_table(
        "code_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("severity", finding_severity, nullable=False),
        sa.Column("category", finding_category, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("explanation", sa.String(2000), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=False),
        sa.Column("deterministic_recommendation", sa.String(2000), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
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
        sa.CheckConstraint("start_line >= 1", name="finding_start_line_positive"),
        sa.CheckConstraint("end_line >= start_line", name="finding_line_range_valid"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="finding_confidence_range"),
        sa.CheckConstraint(
            "path NOT LIKE '/%' AND path NOT LIKE '%:%'", name="finding_path_relative"
        ),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id",
            "repository_file_id",
            "rule_id",
            "start_line",
            "end_line",
            name="uq_code_findings_analysis_location_rule",
        ),
    )
    for column in ("analysis_job_id", "repository_file_id", "rule_id", "severity", "category"):
        op.create_index(f"ix_code_findings_{column}", "code_findings", [column])


def downgrade() -> None:
    for column in ("category", "severity", "rule_id", "repository_file_id", "analysis_job_id"):
        op.drop_index(f"ix_code_findings_{column}", table_name="code_findings")
    op.drop_table("code_findings")
    op.drop_table("analysis_findings_metadata")
    finding_category.drop(op.get_bind(), checkfirst=True)
    finding_severity.drop(op.get_bind(), checkfirst=True)
