from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisJob, AnalysisJobStatus, AnalysisStage, AnalysisStageStatus


class AnalysisJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, analysis_job: AnalysisJob) -> AnalysisJob:
        self._session.add(analysis_job)
        await self._session.flush()
        await self._session.refresh(analysis_job)
        return analysis_job

    async def get_by_id(self, analysis_job_id: UUID) -> AnalysisJob | None:
        result: AnalysisJob | None = await self._session.scalar(
            select(AnalysisJob).where(AnalysisJob.id == analysis_job_id)
        )
        return result

    async def list_for_repository(
        self, repository_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> list[AnalysisJob]:
        statement = (
            select(AnalysisJob)
            .where(AnalysisJob.repository_id == repository_id)
            .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.scalars(statement)).all())

    async def update_status(
        self, analysis_job_id: UUID, status: AnalysisJobStatus
    ) -> AnalysisJob | None:
        statement = (
            update(AnalysisJob)
            .where(AnalysisJob.id == analysis_job_id)
            .values(status=status, updated_at=datetime.now(UTC))
            .returning(AnalysisJob)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def update_progress(
        self, analysis_job_id: UUID, progress_percent: int
    ) -> AnalysisJob | None:
        statement = (
            update(AnalysisJob)
            .where(AnalysisJob.id == analysis_job_id)
            .values(progress_percent=progress_percent, updated_at=datetime.now(UTC))
            .returning(AnalysisJob)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def update_ingestion_state(
        self,
        analysis_job_id: UUID,
        *,
        current_stage: str,
        progress_percent: int,
    ) -> AnalysisJob | None:
        statement = (
            update(AnalysisJob)
            .where(AnalysisJob.id == analysis_job_id)
            .values(
                status=AnalysisJobStatus.RUNNING,
                current_stage=current_stage,
                progress_percent=progress_percent,
                updated_at=datetime.now(UTC),
            )
            .returning(AnalysisJob)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def claim_queued(self, analysis_job_id: UUID) -> AnalysisJob | None:
        now = datetime.now(UTC)
        statement = (
            update(AnalysisJob)
            .where(
                AnalysisJob.id == analysis_job_id,
                AnalysisJob.status == AnalysisJobStatus.QUEUED,
            )
            .values(status=AnalysisJobStatus.RUNNING, started_at=now, updated_at=now)
            .returning(AnalysisJob)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def mark_dispatch_failed(self, analysis_job_id: UUID) -> AnalysisJob | None:
        now = datetime.now(UTC)
        statement = (
            update(AnalysisJob)
            .where(
                AnalysisJob.id == analysis_job_id, AnalysisJob.status == AnalysisJobStatus.QUEUED
            )
            .values(
                status=AnalysisJobStatus.FAILED,
                error_code="analysis_dispatch_failed",
                error_message="The analysis could not be dispatched for processing.",
                completed_at=now,
                updated_at=now,
            )
            .returning(AnalysisJob)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def mark_failed(
        self, analysis_job_id: UUID, *, error_code: str, error_message: str
    ) -> AnalysisJob | None:
        now = datetime.now(UTC)
        statement = (
            update(AnalysisJob)
            .where(AnalysisJob.id == analysis_job_id)
            .values(
                status=AnalysisJobStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                completed_at=now,
                updated_at=now,
            )
            .returning(AnalysisJob)
        )
        return (await self._session.scalars(statement)).one_or_none()


class AnalysisStageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, analysis_stage: AnalysisStage) -> AnalysisStage:
        self._session.add(analysis_stage)
        await self._session.flush()
        await self._session.refresh(analysis_stage)
        return analysis_stage

    async def get_by_id(self, analysis_stage_id: UUID) -> AnalysisStage | None:
        result: AnalysisStage | None = await self._session.scalar(
            select(AnalysisStage).where(AnalysisStage.id == analysis_stage_id)
        )
        return result

    async def list_for_analysis_job(self, analysis_job_id: UUID) -> list[AnalysisStage]:
        statement = (
            select(AnalysisStage)
            .where(AnalysisStage.analysis_job_id == analysis_job_id)
            .order_by(AnalysisStage.created_at, AnalysisStage.id)
        )
        return list((await self._session.scalars(statement)).all())

    async def get_by_name(self, analysis_job_id: UUID, name: str) -> AnalysisStage | None:
        result: AnalysisStage | None = await self._session.scalar(
            select(AnalysisStage).where(
                AnalysisStage.analysis_job_id == analysis_job_id, AnalysisStage.name == name
            )
        )
        return result

    async def update_status(
        self, analysis_stage_id: UUID, status: AnalysisStageStatus
    ) -> AnalysisStage | None:
        statement = (
            update(AnalysisStage)
            .where(AnalysisStage.id == analysis_stage_id)
            .values(status=status, updated_at=datetime.now(UTC))
            .returning(AnalysisStage)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def update_progress(
        self, analysis_stage_id: UUID, progress_percent: int
    ) -> AnalysisStage | None:
        statement = (
            update(AnalysisStage)
            .where(AnalysisStage.id == analysis_stage_id)
            .values(progress_percent=progress_percent, updated_at=datetime.now(UTC))
            .returning(AnalysisStage)
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def update_heartbeat(
        self, analysis_stage_id: UUID, heartbeat_at: datetime
    ) -> AnalysisStage | None:
        statement = (
            update(AnalysisStage)
            .where(AnalysisStage.id == analysis_stage_id)
            .values(heartbeat_at=heartbeat_at, updated_at=datetime.now(UTC))
            .returning(AnalysisStage)
        )
        return (await self._session.scalars(statement)).one_or_none()
