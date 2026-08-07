"""Persist per-analysis parser metadata.

Revision ID: 0004_analysis_parse_metadata
Revises: 0003_parser_persistence
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_analysis_parse_metadata"
down_revision: str | None = "0003_parser_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_parse_metadata",
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("skipped_file_count", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("skipped_file_count >= 0", name="skipped_file_count_nonnegative"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("analysis_job_id"),
    )


def downgrade() -> None:
    op.drop_table("analysis_parse_metadata")
