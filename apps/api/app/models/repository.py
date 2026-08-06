from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import RepositorySourceType, RepositoryStatus
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob


class Repository(TimestampMixin, Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("normalized_url", name="uq_repositories_normalized_url"),
        CheckConstraint("length(trim(owner)) > 0", name="owner_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[RepositorySourceType] = mapped_column(
        enum_type(RepositorySourceType, name="repository_source_type"),
        nullable=False,
        default=RepositorySourceType.GITHUB_PUBLIC,
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(255))
    latest_commit_sha: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[RepositoryStatus] = mapped_column(
        enum_type(RepositoryStatus, name="repository_status"),
        nullable=False,
        default=RepositoryStatus.PENDING,
    )

    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(
        back_populates="repository",
        cascade="save-update, merge",
        passive_deletes=True,
    )
