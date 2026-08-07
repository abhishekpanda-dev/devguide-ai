from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.parsed import RepositoryFile


class AnalysisStructureMetadata(TimestampMixin, Base):
    __tablename__ = "analysis_structure_metadata"
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="RESTRICT"), primary_key=True
    )
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RepositoryFileIntelligence(Base):
    __tablename__ = "repository_file_intelligence"
    __table_args__ = (
        CheckConstraint(
            "entry_point_confidence >= 0 AND entry_point_confidence <= 1",
            name="entry_confidence_range",
        ),
        CheckConstraint("inbound_dependency_count >= 0", name="inbound_count_nonnegative"),
        CheckConstraint("outbound_dependency_count >= 0", name="outbound_count_nonnegative"),
        UniqueConstraint(
            "analysis_job_id", "repository_file_id", name="uq_file_intelligence_analysis_file"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    repository_file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    is_entry_point: Mapped[bool] = mapped_column(nullable=False, default=False)
    entry_point_reason: Mapped[str | None] = mapped_column(String(500))
    entry_point_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    inbound_dependency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outbound_dependency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repository_file: Mapped["RepositoryFile"] = relationship()


class RepositoryDependencyEdge(Base):
    __tablename__ = "repository_dependency_edges"
    __table_args__ = (
        CheckConstraint("source_line >= 1", name="dependency_source_line_positive"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="dependency_confidence_range"),
        CheckConstraint(
            "source_path NOT LIKE '/%' AND source_path NOT LIKE '%:%'",
            name="dependency_source_path_relative",
        ),
        CheckConstraint(
            "target_path NOT LIKE '/%' AND target_path NOT LIKE '%:%'",
            name="dependency_target_path_relative",
        ),
        UniqueConstraint(
            "analysis_job_id",
            "source_repository_file_id",
            "target_repository_file_id",
            "relationship_type",
            "module_name",
            "source_line",
            name="uq_dependency_edge_evidence",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_repository_file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_repository_file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_line: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
