from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.api.dependencies import (
    AccessControlServiceDependency,
    AnalysisJobServiceDependency,
    AnalysisSummaryServiceDependency,
    AuthServiceDependency,
    CodeFindingServiceDependency,
    CurrentUserDependency,
    HealthServiceDependency,
    QualityServiceDependency,
    QuestionReadyAnalysisDependency,
    ReadinessServiceDependency,
    RepositoryIntelligenceAgentDependency,
    RepositoryServiceDependency,
    StructureServiceDependency,
    SubmissionServiceDependency,
    SuggestedFixServiceDependency,
)
from app.core.exceptions import AppError, RepositoryQuestionFailedError
from app.core.middleware import correlation_id_context
from app.models import FindingCategory, FindingSeverity
from app.schemas import (
    AnalysisJobRead,
    AnalysisSummary,
    CodeFindingsResponse,
    QualityResponse,
    RepositoryAgentResponse,
    RepositoryAnalysisListResponse,
    RepositoryQuestionRequest,
    RepositoryRead,
    RepositorySubmissionRequest,
    RepositorySubmissionResponse,
    StructureResponse,
    SuggestedFixResponse,
)
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.schemas.health import HealthResponse

router = APIRouter()


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        max_age=settings.auth_session_hours * 3600,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> AuthResponse:
    user = await service.register(str(payload.email), payload.password)
    _set_session_cookie(response, request, await service.create_session(user))
    return AuthResponse(user=UserRead.model_validate(user))


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> AuthResponse:
    user = await service.authenticate(str(payload.email), payload.password)
    _set_session_cookie(response, request, await service.create_session(user))
    return AuthResponse(user=UserRead.model_validate(user))


@router.get("/auth/me", response_model=AuthResponse)
async def current_user(user: CurrentUserDependency) -> AuthResponse:
    return AuthResponse(user=UserRead.model_validate(user))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    _user: CurrentUserDependency,
) -> None:
    settings = request.app.state.settings
    await service.logout(request.cookies.get(settings.auth_cookie_name))
    response.delete_cookie(settings.auth_cookie_name, path="/")


@router.post(
    "/analyses/{analysis_id}/questions",
    response_model=RepositoryAgentResponse,
    status_code=status.HTTP_200_OK,
)
async def ask_repository_question(
    analysis_id: UUID,
    request: RepositoryQuestionRequest,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
    _analysis: QuestionReadyAnalysisDependency,
    agent: RepositoryIntelligenceAgentDependency,
) -> RepositoryAgentResponse:
    await access.ensure_analysis(_user.id, analysis_id)
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
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
) -> RepositorySubmissionResponse:
    result = await service.submit(request.source_url)
    await access.grant_repository(_user.id, result.repository.id)
    return RepositorySubmissionResponse(
        repository=RepositoryRead.model_validate(result.repository),
        analysis_job=AnalysisJobRead.model_validate(result.analysis_job),
    )


@router.get("/repositories/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    repository_id: UUID,
    service: RepositoryServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
) -> RepositoryRead:
    await access.ensure_repository(_user.id, repository_id)
    repository = await service.get_required(repository_id)
    return RepositoryRead.model_validate(repository)


@router.get("/analyses/{analysis_id}", response_model=AnalysisJobRead)
async def get_analysis(
    analysis_id: UUID,
    service: AnalysisJobServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
) -> AnalysisJobRead:
    await access.ensure_analysis(_user.id, analysis_id)
    analysis = await service.get_required(analysis_id)
    return AnalysisJobRead.model_validate(analysis)


@router.get("/analyses/{analysis_id}/summary", response_model=AnalysisSummary)
async def get_analysis_summary(
    analysis_id: UUID,
    service: AnalysisSummaryServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
) -> AnalysisSummary:
    await access.ensure_analysis(_user.id, analysis_id)
    return await service.get_required(analysis_id)


@router.get("/analyses/{analysis_id}/findings", response_model=CodeFindingsResponse)
async def list_code_findings(
    analysis_id: UUID,
    service: CodeFindingServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
    severity: FindingSeverity | None = None,
    category: FindingCategory | None = None,
    path_prefix: Annotated[str | None, Query(max_length=2048)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CodeFindingsResponse:
    await access.ensure_analysis(_user.id, analysis_id)
    return await service.list_required(
        analysis_id, severity=severity, category=category, path_prefix=path_prefix, limit=limit
    )


@router.post(
    "/analyses/{analysis_id}/findings/{finding_id}/suggested-fix",
    response_model=SuggestedFixResponse,
)
async def generate_suggested_fix(
    analysis_id: UUID,
    finding_id: UUID,
    service: SuggestedFixServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
) -> SuggestedFixResponse:
    await access.ensure_analysis(_user.id, analysis_id)
    return await service.generate(analysis_id, finding_id, correlation_id_context.get())


@router.get("/analyses/{analysis_id}/structure", response_model=StructureResponse)
async def get_repository_structure(
    analysis_id: UUID,
    service: StructureServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
    language: Annotated[str | None, Query(max_length=50)] = None,
    path_prefix: Annotated[str | None, Query(max_length=2048)] = None,
    relationship_type: Annotated[
        str | None, Query(pattern="^(imports|requires|reexports)$")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> StructureResponse:
    await access.ensure_analysis(_user.id, analysis_id)
    return await service.get_required(
        analysis_id,
        language=language,
        path_prefix=path_prefix,
        relationship_type=relationship_type,
        limit=limit,
    )


@router.get("/analyses/{analysis_id}/quality", response_model=QualityResponse)
async def get_repository_quality(
    analysis_id: UUID,
    service: QualityServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
    language: Annotated[str | None, Query(max_length=50)] = None,
    path_prefix: Annotated[str | None, Query(max_length=2048)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> QualityResponse:
    await access.ensure_analysis(_user.id, analysis_id)
    return await service.get_required(
        analysis_id, language=language, path_prefix=path_prefix, limit=limit
    )


@router.get(
    "/repositories/{repository_id}/analyses",
    response_model=RepositoryAnalysisListResponse,
)
async def list_repository_analyses(
    repository_id: UUID,
    repository_service: RepositoryServiceDependency,
    analysis_service: AnalysisJobServiceDependency,
    _user: CurrentUserDependency,
    access: AccessControlServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RepositoryAnalysisListResponse:
    await access.ensure_repository(_user.id, repository_id)
    await repository_service.get_required(repository_id)
    analyses = await analysis_service.list_for_repository(repository_id, limit=limit, offset=offset)
    return RepositoryAnalysisListResponse(
        items=[AnalysisJobRead.model_validate(item) for item in analyses],
        limit=limit,
        offset=offset,
    )
