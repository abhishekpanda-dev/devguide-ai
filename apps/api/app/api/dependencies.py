from typing import Annotated, cast
from uuid import UUID

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents import RepositoryIntelligenceAgent
from app.ai.agents.factory import build_llm_provider
from app.ai.providers import LLMProvider, SuggestedFixProvider
from app.ai.retrieval import SearchRepositorySkill
from app.core.exceptions import (
    AnalysisNotFoundError,
    AnalysisNotReadyError,
    AuthenticationRequiredError,
)
from app.db.session import get_db_session
from app.models import AnalysisJob, AnalysisJobStatus, User
from app.repositories import (
    AnalysisJobRepository,
    CodeFindingRepository,
    ParsedRepository,
    RepositoryQualityRepository,
    RepositoryRepository,
    RepositoryStructureRepository,
)
from app.services import (
    AnalysisJobService,
    AnalysisSummaryService,
    CodeFindingService,
    RepositoryService,
    RepositorySubmissionService,
)
from app.services.access import AccessControlService
from app.services.auth import AuthService
from app.services.feature_location import FeatureLocationService
from app.services.grounded_answer import GroundedAnswerService
from app.services.health import HealthService
from app.services.quality import RepositoryQualityService
from app.services.readiness import DatabaseReadinessService, ReadinessService
from app.services.structure import RepositoryStructureService
from app.services.structure_evidence import StructureEvidenceService
from app.services.suggested_fix import SuggestedFixService


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


def get_auth_service(request: Request, session: AsyncSessionDependency) -> AuthService:
    return AuthService(session, request.app.state.settings.auth_session_hours)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


def get_access_control_service(session: AsyncSessionDependency) -> AccessControlService:
    return AccessControlService(session)


AccessControlServiceDependency = Annotated[
    AccessControlService, Depends(get_access_control_service)
]


async def get_current_user(
    request: Request,
    service: AuthServiceDependency,
    devguide_session: Annotated[str | None, Cookie()] = None,
) -> User:
    settings = request.app.state.settings
    token = request.cookies.get(settings.auth_cookie_name) or devguide_session
    user = await service.resolve_session(token)
    if user is None:
        raise AuthenticationRequiredError
    return user


CurrentUserDependency = Annotated[User, Depends(get_current_user)]


def get_repository_repository(session: AsyncSessionDependency) -> RepositoryRepository:
    return RepositoryRepository(session)


def get_analysis_job_repository(session: AsyncSessionDependency) -> AnalysisJobRepository:
    return AnalysisJobRepository(session)


def get_parsed_repository(session: AsyncSessionDependency) -> ParsedRepository:
    return ParsedRepository(session)


def get_code_finding_repository(session: AsyncSessionDependency) -> CodeFindingRepository:
    return CodeFindingRepository(session)


def get_structure_repository(session: AsyncSessionDependency) -> RepositoryStructureRepository:
    return RepositoryStructureRepository(session)


def get_quality_repository(session: AsyncSessionDependency) -> RepositoryQualityRepository:
    return RepositoryQualityRepository(session)


RepositoryRepositoryDependency = Annotated[RepositoryRepository, Depends(get_repository_repository)]
AnalysisJobRepositoryDependency = Annotated[
    AnalysisJobRepository, Depends(get_analysis_job_repository)
]
ParsedRepositoryDependency = Annotated[ParsedRepository, Depends(get_parsed_repository)]
CodeFindingRepositoryDependency = Annotated[
    CodeFindingRepository, Depends(get_code_finding_repository)
]
StructureRepositoryDependency = Annotated[
    RepositoryStructureRepository, Depends(get_structure_repository)
]
QualityRepositoryDependency = Annotated[
    RepositoryQualityRepository, Depends(get_quality_repository)
]


def get_llm_provider(request: Request) -> LLMProvider:
    return build_llm_provider(request.app.state.settings)


LLMProviderDependency = Annotated[LLMProvider, Depends(get_llm_provider)]


def get_grounded_answer_service(
    request: Request, provider: LLMProviderDependency
) -> GroundedAnswerService:
    return GroundedAnswerService(provider, request.app.state.settings)


GroundedAnswerServiceDependency = Annotated[
    GroundedAnswerService, Depends(get_grounded_answer_service)
]


def get_search_repository_skill(
    repository: ParsedRepositoryDependency,
) -> SearchRepositorySkill:
    return SearchRepositorySkill(repository)


SearchRepositorySkillDependency = Annotated[
    SearchRepositorySkill, Depends(get_search_repository_skill)
]


def get_feature_location_service(
    request: Request,
    jobs: AnalysisJobRepositoryDependency,
    parsed: ParsedRepositoryDependency,
    structures: StructureRepositoryDependency,
    repositories: RepositoryRepositoryDependency,
    findings: CodeFindingRepositoryDependency,
    quality: QualityRepositoryDependency,
) -> FeatureLocationService:
    settings = request.app.state.settings
    return FeatureLocationService(
        jobs,
        parsed,
        structures,
        repositories,
        findings,
        quality,
        maximum_files=settings.feature_location_file_limit,
        neighbor_depth=settings.feature_location_neighbor_depth,
        related_tests_limit=settings.feature_location_test_limit,
    )


FeatureLocationServiceDependency = Annotated[
    FeatureLocationService, Depends(get_feature_location_service)
]


def get_repository_intelligence_agent(
    request: Request,
    search_skill: SearchRepositorySkillDependency,
    answer_service: GroundedAnswerServiceDependency,
    structures: StructureRepositoryDependency,
    feature_location: FeatureLocationServiceDependency,
) -> RepositoryIntelligenceAgent:
    settings = request.app.state.settings
    return RepositoryIntelligenceAgent(
        search_skill,
        answer_service,
        StructureEvidenceService(
            structures,
            file_limit=settings.structure_evidence_file_limit,
            edge_limit=settings.structure_evidence_edge_limit,
            directory_limit=settings.structure_evidence_directory_limit,
        ),
        feature_location,
    )


RepositoryIntelligenceAgentDependency = Annotated[
    RepositoryIntelligenceAgent, Depends(get_repository_intelligence_agent)
]


async def require_question_ready_analysis(
    analysis_id: UUID,
    jobs: AnalysisJobRepositoryDependency,
    parsed: ParsedRepositoryDependency,
) -> AnalysisJob:
    analysis = await jobs.get_by_id(analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError
    if analysis.status not in {AnalysisJobStatus.RUNNING, AnalysisJobStatus.COMPLETED}:
        raise AnalysisNotReadyError
    if not await parsed.has_chunks(analysis_id):
        raise AnalysisNotReadyError
    return analysis


QuestionReadyAnalysisDependency = Annotated[AnalysisJob, Depends(require_question_ready_analysis)]


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


def get_analysis_summary_service(
    jobs: AnalysisJobRepositoryDependency,
    parsed: ParsedRepositoryDependency,
) -> AnalysisSummaryService:
    return AnalysisSummaryService(jobs, parsed)


def get_code_finding_service(
    jobs: AnalysisJobRepositoryDependency,
    repositories: RepositoryRepositoryDependency,
    findings: CodeFindingRepositoryDependency,
) -> CodeFindingService:
    return CodeFindingService(jobs, repositories, findings)


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
AnalysisSummaryServiceDependency = Annotated[
    AnalysisSummaryService, Depends(get_analysis_summary_service)
]
CodeFindingServiceDependency = Annotated[CodeFindingService, Depends(get_code_finding_service)]


def get_suggested_fix_service(
    request: Request,
    jobs: AnalysisJobRepositoryDependency,
    repositories: RepositoryRepositoryDependency,
    findings: CodeFindingRepositoryDependency,
    parsed: ParsedRepositoryDependency,
    provider: LLMProviderDependency,
) -> SuggestedFixService:
    return SuggestedFixService(
        jobs,
        repositories,
        findings,
        parsed,
        cast(SuggestedFixProvider, provider),
        request.app.state.settings,
    )


SuggestedFixServiceDependency = Annotated[SuggestedFixService, Depends(get_suggested_fix_service)]


def get_structure_service(
    jobs: AnalysisJobRepositoryDependency,
    repositories: RepositoryRepositoryDependency,
    structures: StructureRepositoryDependency,
) -> RepositoryStructureService:
    return RepositoryStructureService(jobs, repositories, structures)


StructureServiceDependency = Annotated[RepositoryStructureService, Depends(get_structure_service)]


def get_quality_service(
    jobs: AnalysisJobRepositoryDependency,
    repositories: RepositoryRepositoryDependency,
    quality: QualityRepositoryDependency,
) -> RepositoryQualityService:
    return RepositoryQualityService(jobs, repositories, quality)


QualityServiceDependency = Annotated[RepositoryQualityService, Depends(get_quality_service)]
SubmissionServiceDependency = Annotated[
    RepositorySubmissionService, Depends(get_submission_service)
]
