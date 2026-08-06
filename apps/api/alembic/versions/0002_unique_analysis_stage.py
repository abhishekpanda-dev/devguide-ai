"""Prevent duplicate stages for one analysis job.

Revision ID: 0002_unique_analysis_stage
Revises: 0001_repository_analysis
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_unique_analysis_stage"
down_revision: str | None = "0001_repository_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_analysis_stages_job_name", "analysis_stages", ["analysis_job_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_analysis_stages_job_name", "analysis_stages", type_="unique")
