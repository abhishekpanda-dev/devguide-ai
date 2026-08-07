from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    AnalysisJobServiceDependency,
    HealthServiceDependency,
    QuestionReadyAnalysisDependency,
    ReadinessServiceDependency,
    RepositoryIntelligenceAgentDependency,
    RepositoryServiceDependency,
    SubmissionServiceDependency,
)
from app.core.exceptions import AppError, RepositoryQuestionFailedError
from app.core.middleware import correlation_id_context
from app.schemas import (
    AnalysisJobRead,
    RepositoryAgentResponse,
    RepositoryAnalysisListResponse,
    RepositoryQuestionRequest,
    RepositoryRead,
    RepositorySubmissionRequest,
    RepositorySubmissionResponse,
)
from app.schemas.health import HealthResponse

router = APIRouter()


@router.post(
    "/analyses/{analysis_id}/questions",
    response_model=RepositoryAgentResponse,
    status_code=status.HTTP_200_OK,
)
async def ask_repository_question(
    analysis_id: UUID,
    request: RepositoryQuestionRequest,
    _analysis: QuestionReadyAnalysisDependency,
    agent: RepositoryIntelligenceAgentDependency,
) -> RepositoryAgentResponse:
    agent_request = request.to_agent_request(
        analysis_job_id=analysis_id,
        correlation_id=correlation_id_context.get(),
    )
    try:
        return await agent.run(agent_request)
    except AppError as exc:
        raise RepositoryQuestionFailedError from exc


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health(service: HealthServiceDependency) -> HealthResponse:
    return service.get_health()


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "A required dependency is unavailable."
        }
    },
)
async def ready(service: ReadinessServiceDependency) -> HealthResponse:
    await service.ensure_ready()
    return service.get_status()


@router.post(
    "/repositories",
    response_model=RepositorySubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_repository(
    request: RepositorySubmissionRequest,
    service: SubmissionServiceDependency,
) -> RepositorySubmissionResponse:
    result = await service.submit(request.source_url)
    return RepositorySubmissionResponse(
        repository=RepositoryRead.model_validate(result.repository),
        analysis_job=AnalysisJobRead.model_validate(result.analysis_job),
    )


@router.get("/repositories/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    repository_id: UUID,
    service: RepositoryServiceDependency,
) -> RepositoryRead:
    repository = await service.get_required(repository_id)
    return RepositoryRead.model_validate(repository)


@router.get("/analyses/{analysis_id}", response_model=AnalysisJobRead)
async def get_analysis(
    analysis_id: UUID,
    service: AnalysisJobServiceDependency,
) -> AnalysisJobRead:
    analysis = await service.get_required(analysis_id)
    return AnalysisJobRead.model_validate(analysis)


@router.get(
    "/repositories/{repository_id}/analyses",
    response_model=RepositoryAnalysisListResponse,
)
async def list_repository_analyses(
    repository_id: UUID,
    repository_service: RepositoryServiceDependency,
    analysis_service: AnalysisJobServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RepositoryAnalysisListResponse:
    await repository_service.get_required(repository_id)
    analyses = await analysis_service.list_for_repository(repository_id, limit=limit, offset=offset)
    return RepositoryAnalysisListResponse(
        items=[AnalysisJobRead.model_validate(item) for item in analyses],
        limit=limit,
        offset=offset,
    )
