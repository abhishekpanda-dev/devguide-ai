from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AnalysisJobStatus, AnalysisStageStatus
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.repository import Repository


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint("progress_percent BETWEEN 0 AND 100", name="progress_percent_range"),
        CheckConstraint("length(trim(pipeline_version)) > 0", name="pipeline_version_not_empty"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    repository_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[AnalysisJobStatus] = mapped_column(
        enum_type(AnalysisJobStatus, name="analysis_job_status"),
        nullable=False,
        default=AnalysisJobStatus.QUEUED,
    )
    current_stage: Mapped[str | None] = mapped_column(String(255))
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_version: Mapped[str] = mapped_column(String(100), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(2000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    repository: Mapped["Repository"] = relationship(back_populates="analysis_jobs")
    stages: Mapped[list["AnalysisStage"]] = relationship(
        back_populates="analysis_job",
        cascade="save-update, merge",
        passive_deletes=True,
    )


class AnalysisStage(TimestampMixin, Base):
    __tablename__ = "analysis_stages"
    __table_args__ = (
        CheckConstraint("progress_percent BETWEEN 0 AND 100", name="progress_percent_range"),
        CheckConstraint("attempt >= 1", name="attempt_at_least_one"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        UniqueConstraint("analysis_job_id", "name", name="uq_analysis_stages_job_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AnalysisStageStatus] = mapped_column(
        enum_type(AnalysisStageStatus, name="analysis_stage_status"),
        nullable=False,
        default=AnalysisStageStatus.PENDING,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(2000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    analysis_job: Mapped[AnalysisJob] = relationship(back_populates="stages")
