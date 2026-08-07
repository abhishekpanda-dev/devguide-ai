from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.repository_intelligence import RepositoryIntelligenceAgent
from app.ai.providers import ClaudeProvider, LLMProvider, MockLLMProvider
from app.ai.providers.claude import ClaudeClient
from app.ai.retrieval import SearchRepositorySkill
from app.core.config import Settings
from app.core.exceptions import AIProviderNotConfiguredError
from app.repositories import ParsedRepository, RepositoryStructureRepository
from app.services.grounded_answer import GroundedAnswerService
from app.services.structure_evidence import StructureEvidenceService


def build_repository_intelligence_agent(
    *,
    session: AsyncSession,
    settings: Settings,
    provider: LLMProvider | None = None,
) -> RepositoryIntelligenceAgent:
    selected = provider or build_llm_provider(settings)
    search_skill = SearchRepositorySkill(ParsedRepository(session))
    answer_service = GroundedAnswerService(selected, settings)
    return RepositoryIntelligenceAgent(
        search_skill,
        answer_service,
        StructureEvidenceService(
            RepositoryStructureRepository(session),
            file_limit=settings.structure_evidence_file_limit,
            edge_limit=settings.structure_evidence_edge_limit,
            directory_limit=settings.structure_evidence_directory_limit,
        ),
    )


def build_llm_provider(
    settings: Settings, *, claude_client: ClaudeClient | None = None
) -> LLMProvider:
    if settings.ai_provider_name == "mock":
        if settings.environment not in {"local", "test"}:
            raise AIProviderNotConfiguredError
        return MockLLMProvider()
    return ClaudeProvider(
        api_key=(
            settings.anthropic_api_key.get_secret_value()
            if settings.anthropic_api_key is not None
            else None
        ),
        model=settings.claude_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        retry_count=settings.ai_retry_count,
        client=claude_client,
    )
