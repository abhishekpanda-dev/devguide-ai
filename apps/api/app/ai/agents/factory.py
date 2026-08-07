from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.repository_intelligence import RepositoryIntelligenceAgent
from app.ai.providers import ClaudeProvider, LLMProvider, MockLLMProvider
from app.ai.retrieval import SearchRepositorySkill
from app.core.config import Settings
from app.repositories import ParsedRepository
from app.services.grounded_answer import GroundedAnswerService


def build_repository_intelligence_agent(
    *,
    session: AsyncSession,
    settings: Settings,
    provider: LLMProvider | None = None,
) -> RepositoryIntelligenceAgent:
    selected = provider or _build_provider(settings)
    search_skill = SearchRepositorySkill(ParsedRepository(session))
    answer_service = GroundedAnswerService(selected, settings)
    return RepositoryIntelligenceAgent(search_skill, answer_service)


def _build_provider(settings: Settings) -> LLMProvider:
    if settings.ai_provider_name == "mock":
        return MockLLMProvider()
    return ClaudeProvider(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        retry_count=settings.ai_retry_count,
    )
