from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import FindingCategory, FindingSeverity
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.parsed import RepositoryFile


class CodeFinding(TimestampMixin, Base):
    __tablename__ = "code_findings"
    __table_args__ = (
        CheckConstraint("start_line >= 1", name="finding_start_line_positive"),
        CheckConstraint("end_line >= start_line", name="finding_line_range_valid"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="finding_confidence_range"),
        CheckConstraint("path NOT LIKE '/%' AND path NOT LIKE '%:%'", name="finding_path_relative"),
        UniqueConstraint(
            "analysis_job_id",
            "repository_file_id",
            "rule_id",
            "start_line",
            "end_line",
            name="uq_code_findings_analysis_location_rule",
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
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[FindingSeverity] = mapped_column(
        enum_type(FindingSeverity, name="finding_severity"), nullable=False, index=True
    )
    category: Mapped[FindingCategory] = mapped_column(
        enum_type(FindingCategory, name="finding_category"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    deterministic_recommendation: Mapped[str] = mapped_column(String(2000), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_job: Mapped["AnalysisJob"] = relationship()
    repository_file: Mapped["RepositoryFile"] = relationship()


class AnalysisFindingsMetadata(TimestampMixin, Base):
    __tablename__ = "analysis_findings_metadata"
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="RESTRICT"), primary_key=True
    )
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
