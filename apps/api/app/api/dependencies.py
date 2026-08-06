from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.services import AnalysisJobService, RepositoryService, RepositorySubmissionService
from app.services.health import HealthService
from app.services.readiness import DatabaseReadinessService, ReadinessService


def get_health_service(request: Request) -> HealthService:
    return HealthService(version=request.app.state.settings.app_version)


def get_readiness_service(request: Request) -> ReadinessService:
    return DatabaseReadinessService(
        session_factory=request.app.state.session_factory,
        version=request.app.state.settings.app_version,
    )


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]
ReadinessServiceDependency = Annotated[ReadinessService, Depends(get_readiness_service)]

AsyncSessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


def get_repository_repository(session: AsyncSessionDependency) -> RepositoryRepository:
    return RepositoryRepository(session)


def get_analysis_job_repository(session: AsyncSessionDependency) -> AnalysisJobRepository:
    return AnalysisJobRepository(session)


RepositoryRepositoryDependency = Annotated[RepositoryRepository, Depends(get_repository_repository)]
AnalysisJobRepositoryDependency = Annotated[
    AnalysisJobRepository, Depends(get_analysis_job_repository)
]


def get_repository_service(
    session: AsyncSessionDependency,
    repository: RepositoryRepositoryDependency,
) -> RepositoryService:
    return RepositoryService(session, repository)


def get_analysis_job_service(
    session: AsyncSessionDependency,
    repository: AnalysisJobRepositoryDependency,
) -> AnalysisJobService:
    return AnalysisJobService(session, repository)


def get_submission_service(
    request: Request,
    session: AsyncSessionDependency,
    repositories: RepositoryRepositoryDependency,
    analysis_jobs: AnalysisJobRepositoryDependency,
) -> RepositorySubmissionService:
    return RepositorySubmissionService(
        session=session,
        repositories=repositories,
        analysis_jobs=analysis_jobs,
        pipeline_version=request.app.state.settings.analysis_pipeline_version,
        queue=request.app.state.analysis_queue,
    )


RepositoryServiceDependency = Annotated[RepositoryService, Depends(get_repository_service)]
AnalysisJobServiceDependency = Annotated[AnalysisJobService, Depends(get_analysis_job_service)]
SubmissionServiceDependency = Annotated[
    RepositorySubmissionService, Depends(get_submission_service)
]
