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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AnalysisQualityMetadata(TimestampMixin, Base):
    __tablename__ = "analysis_quality_metadata"
    __table_args__ = (
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="quality_score_range"),
    )
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="RESTRICT"), primary_key=True
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    category_scores: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    deductions: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    score_version: Mapped[str] = mapped_column(String(100), nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class UnusedCodeCandidateModel(Base):
    __tablename__ = "unused_code_candidates"
    __table_args__ = (
        CheckConstraint("start_line >= 1 AND end_line >= start_line", name="unused_line_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="unused_confidence_range"),
        UniqueConstraint(
            "analysis_job_id",
            "repository_file_id",
            "symbol_name",
            "start_line",
            name="uq_unused_candidate",
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
        Uuid(as_uuid=True), ForeignKey("repository_files.id", ondelete="RESTRICT"), nullable=False
    )
    symbol_name: Mapped[str] = mapped_column(String(512), nullable=False)
    symbol_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(2000), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)


class DuplicateCodeGroup(Base):
    __tablename__ = "duplicate_code_groups"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(2000), nullable=False)


class DuplicateCodeMember(Base):
    __tablename__ = "duplicate_code_members"
    __table_args__ = (
        UniqueConstraint(
            "analysis_job_id",
            "group_id",
            "repository_file_id",
            "start_line",
            name="uq_duplicate_member",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    repository_file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repository_files.id", ondelete="RESTRICT"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
