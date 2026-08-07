"""Persist repository structure intelligence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_repository_structure"
down_revision: str | None = "0005_code_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_structure_metadata",
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
        "repository_file_intelligence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("is_entry_point", sa.Boolean(), nullable=False),
        sa.Column("entry_point_reason", sa.String(500)),
        sa.Column("entry_point_confidence", sa.Float(), nullable=False),
        sa.Column("inbound_dependency_count", sa.Integer(), nullable=False),
        sa.Column("outbound_dependency_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "entry_point_confidence >= 0 AND entry_point_confidence <= 1",
            name="entry_confidence_range",
        ),
        sa.CheckConstraint("inbound_dependency_count >= 0", name="inbound_count_nonnegative"),
        sa.CheckConstraint("outbound_dependency_count >= 0", name="outbound_count_nonnegative"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id", "repository_file_id", name="uq_file_intelligence_analysis_file"
        ),
    )
    op.create_index(
        "ix_repository_file_intelligence_analysis_job_id",
        "repository_file_intelligence",
        ["analysis_job_id"],
    )
    op.create_index(
        "ix_repository_file_intelligence_repository_file_id",
        "repository_file_intelligence",
        ["repository_file_id"],
    )
    op.create_table(
        "repository_dependency_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("source_repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("target_repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("module_name", sa.String(1000), nullable=False),
        sa.Column("source_path", sa.String(2048), nullable=False),
        sa.Column("target_path", sa.String(2048), nullable=False),
        sa.Column("source_line", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("source_line >= 1", name="dependency_source_line_positive"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="dependency_confidence_range"
        ),
        sa.CheckConstraint(
            "source_path NOT LIKE '/%' AND source_path NOT LIKE '%:%'",
            name="dependency_source_path_relative",
        ),
        sa.CheckConstraint(
            "target_path NOT LIKE '/%' AND target_path NOT LIKE '%:%'",
            name="dependency_target_path_relative",
        ),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id",
            "source_repository_file_id",
            "target_repository_file_id",
            "relationship_type",
            "module_name",
            "source_line",
            name="uq_dependency_edge_evidence",
        ),
    )
    for column in (
        "analysis_job_id",
        "source_repository_file_id",
        "target_repository_file_id",
        "relationship_type",
    ):
        op.create_index(
            f"ix_repository_dependency_edges_{column}", "repository_dependency_edges", [column]
        )


def downgrade() -> None:
    for column in (
        "relationship_type",
        "target_repository_file_id",
        "source_repository_file_id",
        "analysis_job_id",
    ):
        op.drop_index(
            f"ix_repository_dependency_edges_{column}", table_name="repository_dependency_edges"
        )
    op.drop_table("repository_dependency_edges")
    op.drop_index(
        "ix_repository_file_intelligence_repository_file_id",
        table_name="repository_file_intelligence",
    )
    op.drop_index(
        "ix_repository_file_intelligence_analysis_job_id", table_name="repository_file_intelligence"
    )
    op.drop_table("repository_file_intelligence")
    op.drop_table("analysis_structure_metadata")
