from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.repository import Repository


class RepositoryFile(TimestampMixin, Base):
    __tablename__ = "repository_files"
    __table_args__ = (
        UniqueConstraint("analysis_job_id", "path", name="uq_repository_files_analysis_path"),
        CheckConstraint("size_bytes >= 0", name="size_bytes_nonnegative"),
        CheckConstraint("line_count >= 0", name="line_count_nonnegative"),
        CheckConstraint("length(trim(content_hash)) > 0", name="content_hash_not_empty"),
        CheckConstraint("path NOT LIKE '/%' AND path NOT LIKE '%:%'", name="path_relative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    repository_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_documentation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_configuration: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    encoding: Mapped[str | None] = mapped_column(String(50))
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    repository: Mapped["Repository"] = relationship()
    analysis_job: Mapped["AnalysisJob"] = relationship()
    chunks: Mapped[list["CodeChunk"]] = relationship(
        cascade="save-update, merge", passive_deletes=True
    )


class CodeChunk(Base):
    __tablename__ = "code_chunks"
    __table_args__ = (
        UniqueConstraint("analysis_job_id", "id", name="uq_code_chunks_analysis_chunk"),
        CheckConstraint("start_line >= 1", name="start_line_positive"),
        CheckConstraint("end_line >= start_line", name="line_range_valid"),
        CheckConstraint("length(trim(content_hash)) > 0", name="content_hash_not_empty"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repository_file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
