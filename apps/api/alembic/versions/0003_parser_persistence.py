"""Add parser persistence tables.

Revision ID: 0003_parser_persistence
Revises: 0002_unique_analysis_stage
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_parser_persistence"
down_revision: str | None = "0002_unique_analysis_stage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repository_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("extension", sa.String(32), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("is_test", sa.Boolean(), nullable=False),
        sa.Column("is_documentation", sa.Boolean(), nullable=False),
        sa.Column("is_configuration", sa.Boolean(), nullable=False),
        sa.Column("is_generated", sa.Boolean(), nullable=False),
        sa.Column("encoding", sa.String(50)),
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
        sa.CheckConstraint("size_bytes >= 0", name="size_bytes_nonnegative"),
        sa.CheckConstraint("line_count >= 0", name="line_count_nonnegative"),
        sa.CheckConstraint("length(trim(content_hash)) > 0", name="content_hash_not_empty"),
        sa.CheckConstraint("path NOT LIKE '/%' AND path NOT LIKE '%:%'", name="path_relative"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_job_id", "path", name="uq_repository_files_analysis_path"),
    )
    op.create_index("ix_repository_files_repository_id", "repository_files", ["repository_id"])
    op.create_index("ix_repository_files_analysis_job_id", "repository_files", ["analysis_job_id"])
    op.create_table(
        "code_chunks",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("parser_version", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("start_line >= 1", name="start_line_positive"),
        sa.CheckConstraint("end_line >= start_line", name="line_range_valid"),
        sa.CheckConstraint("length(trim(content_hash)) > 0", name="content_hash_not_empty"),
        sa.ForeignKeyConstraint(
            ["repository_file_id"], ["repository_files.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", "analysis_job_id"),
        sa.UniqueConstraint("analysis_job_id", "id", name="uq_code_chunks_analysis_chunk"),
    )
    op.create_index("ix_code_chunks_repository_file_id", "code_chunks", ["repository_file_id"])
    op.create_index("ix_code_chunks_analysis_job_id", "code_chunks", ["analysis_job_id"])


def downgrade() -> None:
    op.drop_index("ix_code_chunks_analysis_job_id", table_name="code_chunks")
    op.drop_index("ix_code_chunks_repository_file_id", table_name="code_chunks")
    op.drop_table("code_chunks")
    op.drop_index("ix_repository_files_analysis_job_id", table_name="repository_files")
    op.drop_index("ix_repository_files_repository_id", table_name="repository_files")
    op.drop_table("repository_files")
