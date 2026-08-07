from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents import RepositoryIntelligenceAgent
from app.ai.providers import ClaudeProvider, LLMProvider, MockLLMProvider
from app.ai.retrieval import SearchRepositorySkill
from app.core.exceptions import (
    AIProviderNotConfiguredError,
    AnalysisNotFoundError,
    AnalysisNotReadyError,
)
from app.db.session import get_db_session
from app.models import AnalysisJob, AnalysisJobStatus
from app.repositories import AnalysisJobRepository, ParsedRepository, RepositoryRepository
from app.services import AnalysisJobService, RepositoryService, RepositorySubmissionService
from app.services.grounded_answer import GroundedAnswerService
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


def get_parsed_repository(session: AsyncSessionDependency) -> ParsedRepository:
    return ParsedRepository(session)


RepositoryRepositoryDependency = Annotated[RepositoryRepository, Depends(get_repository_repository)]
AnalysisJobRepositoryDependency = Annotated[
    AnalysisJobRepository, Depends(get_analysis_job_repository)
]
ParsedRepositoryDependency = Annotated[ParsedRepository, Depends(get_parsed_repository)]


def get_llm_provider(request: Request) -> LLMProvider:
    settings = request.app.state.settings
    if settings.ai_provider_name == "mock":
        if settings.environment not in {"local", "test"}:
            raise AIProviderNotConfiguredError
        return MockLLMProvider()
    return ClaudeProvider(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        retry_count=settings.ai_retry_count,
    )


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


def get_repository_intelligence_agent(
    search_skill: SearchRepositorySkillDependency,
    answer_service: GroundedAnswerServiceDependency,
) -> RepositoryIntelligenceAgent:
    return RepositoryIntelligenceAgent(search_skill, answer_service)


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
