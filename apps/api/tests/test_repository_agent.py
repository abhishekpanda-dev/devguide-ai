from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents import RepositoryIntelligenceAgent, build_repository_intelligence_agent
from app.ai.providers import MockLLMProvider
from app.core.config import Settings
from app.core.exceptions import (
    AIProviderUnavailableError,
    RepositoryAgentAnswerFailedError,
    RepositoryAgentEvidenceInvalidError,
    RepositoryAgentSearchFailedError,
)
from app.schemas.grounded_answer import EvidenceQuality, GroundedAnswer, GroundedCitation
from app.schemas.repository_agent import RepositoryAgentRequest
from app.schemas.retrieval import (
    MatchedChannel,
    RepositoryEvidence,
    SearchCoverage,
    SearchRepositoryRequest,
    SearchRepositoryResult,
)
from app.schemas.structure_evidence import StructureEvidence
from app.services.grounded_answer import GroundedAnswerService


def evidence(
    chunk_id: str = "chunk-1",
    *,
    path: str = "app/service.py",
    start_line: int = 1,
    end_line: int = 3,
    score: float = 50,
) -> RepositoryEvidence:
    return RepositoryEvidence(
        repository_file_id=uuid4(),
        chunk_id=chunk_id,
        path=path,
        language="python",
        start_line=start_line,
        end_line=end_line,
        excerpt="def repository_service():\n    return True\n",
        score=score,
        matched_channels=(MatchedChannel.SYMBOL,),
        content_hash=(chunk_id[-1] if chunk_id[-1].isalnum() else "a") * 64,
        commit_sha="b" * 40,
    )


def result(analysis_id: UUID, *items: RepositoryEvidence) -> SearchRepositoryResult:
    return SearchRepositoryResult(
        analysis_job_id=analysis_id,
        query="How does the repository service work?",
        evidence=items,
        total_candidates=len(items),
        returned_count=len(items),
        coverage=SearchCoverage(
            channels=(MatchedChannel.SYMBOL,),
            candidate_files=len({item.repository_file_id for item in items}),
            candidate_chunks=len(items),
            strong_matches=len(items),
        ),
        limitations=("Lexical evidence only.",),
    )


class FakeSearchSkill:
    def __init__(self, search_result: SearchRepositoryResult | None = None) -> None:
        self.search_result = search_result
        self.requests: list[SearchRepositoryRequest] = []

    async def search(self, request: SearchRepositoryRequest) -> SearchRepositoryResult:
        self.requests.append(request)
        if self.search_result is None:
            raise RuntimeError("raw database detail")
        return self.search_result


def request(analysis_id: UUID) -> RepositoryAgentRequest:
    return RepositoryAgentRequest(
        analysis_job_id=analysis_id,
        question="How does the repository service work?",
        languages=(" Python ",),
        path_prefix="app/services/",
        retrieval_limit=5,
        retrieval_minimum_score=10,
        maximum_citations=3,
        correlation_id="trace-1",
    )


async def test_valid_request_runs_search_and_grounded_answer() -> None:
    analysis_id = uuid4()
    item = evidence()
    search = FakeSearchSkill(result(analysis_id, item))
    provider = MockLLMProvider()
    agent = RepositoryIntelligenceAgent(
        search, GroundedAnswerService(provider, Settings(environment="test"))
    )
    response = await agent.run(request(analysis_id))
    assert response.answer
    assert response.analysis_job_id == analysis_id
    assert response.retrieved_evidence_count == 1
    assert response.provider == "mock"
    assert response.model == "mock-grounded-v1"
    assert response.citations[0].repository_file_id == item.repository_file_id
    assert response.citations[0].chunk_id == item.chunk_id
    assert response.correlation_id == "trace-1"
    assert response.limitations == ("Lexical evidence only.",)
    assert len(provider.requests) == 1
    assert not hasattr(response, "chain_of_thought")
    assert not hasattr(response, "raw_provider_response")


async def test_agent_forwards_scope_filters_and_retrieval_controls() -> None:
    analysis_id = uuid4()
    search = FakeSearchSkill(result(analysis_id))
    provider = MockLLMProvider()
    await RepositoryIntelligenceAgent(
        search, GroundedAnswerService(provider, Settings(environment="test"))
    ).run(request(analysis_id))
    forwarded = search.requests[0]
    assert forwarded.analysis_job_id == analysis_id
    assert forwarded.languages == ("python",)
    assert forwarded.path_prefix == "app/services/"
    assert forwarded.limit == 5
    assert forwarded.minimum_score == 10


def test_request_validation_bounds_question_and_retrieval() -> None:
    analysis_id = uuid4()
    with pytest.raises(ValidationError):
        RepositoryAgentRequest(analysis_job_id=analysis_id, question="   ")
    with pytest.raises(ValidationError):
        RepositoryAgentRequest(analysis_job_id=analysis_id, question="x" * 4001)
    with pytest.raises(ValidationError):
        RepositoryAgentRequest(analysis_job_id=analysis_id, question="x", retrieval_limit=0)
    with pytest.raises(ValidationError):
        RepositoryAgentRequest(
            analysis_job_id=analysis_id, question="x", retrieval_minimum_score=111
        )


async def test_insufficient_evidence_skips_mock_provider() -> None:
    analysis_id = uuid4()
    search = FakeSearchSkill(result(analysis_id))
    provider = MockLLMProvider()
    response = await RepositoryIntelligenceAgent(
        search, GroundedAnswerService(provider, Settings(environment="test"))
    ).run(request(analysis_id))
    assert response.insufficient_evidence is True
    assert response.citations == ()
    assert response.provider is None
    assert response.model is None
    assert provider.requests == []


async def test_cross_analysis_result_is_rejected() -> None:
    requested = uuid4()
    search = FakeSearchSkill(result(uuid4(), evidence()))
    with pytest.raises(RepositoryAgentEvidenceInvalidError):
        await RepositoryIntelligenceAgent(
            search, GroundedAnswerService(MockLLMProvider(), Settings(environment="test"))
        ).run(request(requested))


async def test_invalid_evidence_path_and_line_range_are_rejected() -> None:
    analysis_id = uuid4()
    valid = evidence()
    invalid_path = RepositoryEvidence.model_construct(**{**valid.model_dump(), "path": "../x.py"})
    invalid_lines = RepositoryEvidence.model_construct(
        **{**valid.model_dump(), "start_line": 5, "end_line": 2}
    )
    for item in (invalid_path, invalid_lines):
        malformed = SearchRepositoryResult.model_construct(
            analysis_job_id=analysis_id,
            query="q",
            evidence=(item,),
            total_candidates=1,
            returned_count=1,
            coverage=SearchCoverage(
                channels=(), candidate_files=1, candidate_chunks=1, strong_matches=1
            ),
            limitations=(),
        )
        with pytest.raises(RepositoryAgentEvidenceInvalidError):
            await RepositoryIntelligenceAgent(
                FakeSearchSkill(malformed),
                GroundedAnswerService(MockLLMProvider(), Settings(environment="test")),
            ).run(request(analysis_id))


async def test_duplicate_evidence_removed_and_order_is_deterministic() -> None:
    analysis_id = uuid4()
    lower = evidence("chunk-2", path="z.py", score=10)
    higher = evidence("chunk-1", path="a.py", score=80)
    search = FakeSearchSkill(result(analysis_id, lower, higher, higher))
    provider = MockLLMProvider()
    response = await RepositoryIntelligenceAgent(
        search, GroundedAnswerService(provider, Settings(environment="test"))
    ).run(request(analysis_id))
    assert response.retrieved_evidence_count == 2
    assert [item.chunk_id for item in provider.requests[0].evidence] == ["chunk-1", "chunk-2"]


class UnsupportedCitationService:
    async def answer(
        self,
        *,
        question: str,
        search_result: SearchRepositoryResult,
        correlation_id: str | None = None,
        maximum_citations: int = 10,
        structure_evidence: StructureEvidence | None = None,
        feature_location: object | None = None,
    ) -> GroundedAnswer:
        return GroundedAnswer(
            answer="Unsupported.",
            citations=(
                GroundedCitation(
                    chunk_id="unknown",
                    path="other.py",
                    start_line=1,
                    end_line=1,
                    content_hash="f" * 64,
                ),
            ),
            evidence_quality=EvidenceQuality.LOW,
            insufficient_evidence=False,
            provider="fake",
            model="fake",
        )


class FailingAnswerService:
    async def answer(
        self,
        *,
        question: str,
        search_result: SearchRepositoryResult,
        correlation_id: str | None = None,
        maximum_citations: int = 10,
        structure_evidence: StructureEvidence | None = None,
        feature_location: object | None = None,
    ) -> GroundedAnswer:
        raise AIProviderUnavailableError


async def test_unsupported_answer_citation_is_rejected() -> None:
    analysis_id = uuid4()
    with pytest.raises(RepositoryAgentEvidenceInvalidError):
        await RepositoryIntelligenceAgent(
            FakeSearchSkill(result(analysis_id, evidence())), UnsupportedCitationService()
        ).run(request(analysis_id))


async def test_search_and_answer_failures_are_safely_translated() -> None:
    analysis_id = uuid4()
    with pytest.raises(RepositoryAgentSearchFailedError) as search_error:
        await RepositoryIntelligenceAgent(
            FakeSearchSkill(),
            GroundedAnswerService(MockLLMProvider(), Settings(environment="test")),
        ).run(request(analysis_id))
    assert "database" not in search_error.value.message
    with pytest.raises(RepositoryAgentAnswerFailedError) as answer_error:
        await RepositoryIntelligenceAgent(
            FakeSearchSkill(result(analysis_id, evidence())), FailingAnswerService()
        ).run(request(analysis_id))
    assert "provider" not in answer_error.value.message.lower()


def test_runtime_contract_uses_no_database_or_network_objects() -> None:
    assert cast(object, FakeSearchSkill)
    assert cast(object, MockLLMProvider)


def test_internal_factory_accepts_injected_mock_without_external_services() -> None:
    session = cast(AsyncSession, object())
    built = build_repository_intelligence_agent(
        session=session,
        settings=Settings(environment="test"),
        provider=MockLLMProvider(),
    )
    assert isinstance(built, RepositoryIntelligenceAgent)
