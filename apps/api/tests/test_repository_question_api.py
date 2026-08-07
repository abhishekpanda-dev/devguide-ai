from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.ai.providers import MockLLMProvider
from app.api.dependencies import (
    get_llm_provider,
    get_repository_intelligence_agent,
    get_search_repository_skill,
    require_question_ready_analysis,
)
from app.core.exceptions import (
    AnalysisNotFoundError,
    AnalysisNotReadyError,
    RepositoryAgentSearchFailedError,
)
from app.models import AnalysisJob, AnalysisJobStatus
from app.repositories import AnalysisJobRepository, ParsedRepository
from app.schemas.grounded_answer import EvidenceQuality
from app.schemas.repository_agent import (
    RepositoryAgentCitation,
    RepositoryAgentRequest,
    RepositoryAgentResponse,
)
from app.schemas.retrieval import (
    MatchedChannel,
    RepositoryEvidence,
    SearchCoverage,
    SearchRepositoryRequest,
    SearchRepositoryResult,
)


def evidence() -> RepositoryEvidence:
    return RepositoryEvidence(
        repository_file_id=uuid4(),
        chunk_id="chunk-1",
        path="app/auth.py",
        language="python",
        start_line=1,
        end_line=4,
        excerpt="def authenticate():\n    return True\n",
        score=60,
        matched_channels=(MatchedChannel.SYMBOL,),
        content_hash="a" * 64,
        commit_sha="b" * 40,
    )


def search_result(analysis_id: UUID, *items: RepositoryEvidence) -> SearchRepositoryResult:
    return SearchRepositoryResult(
        analysis_job_id=analysis_id,
        query="Where is authentication implemented?",
        evidence=items,
        total_candidates=len(items),
        returned_count=len(items),
        coverage=SearchCoverage(
            channels=(MatchedChannel.SYMBOL,),
            candidate_files=len(items),
            candidate_chunks=len(items),
            strong_matches=len(items),
        ),
        limitations=() if items else ("No matching lexical evidence.",),
    )


class FakeSearchSkill:
    def __init__(self, result: SearchRepositoryResult) -> None:
        self.result = result
        self.requests: list[SearchRepositoryRequest] = []

    async def search(self, request: SearchRepositoryRequest) -> SearchRepositoryResult:
        self.requests.append(request)
        return self.result


async def ready_analysis(analysis_id: UUID) -> AnalysisJob:
    return AnalysisJob(id=analysis_id, repository_id=uuid4(), pipeline_version="1")


def configure_runtime(
    app: FastAPI,
    analysis_id: UUID,
    *items: RepositoryEvidence,
) -> tuple[FakeSearchSkill, MockLLMProvider]:
    search = FakeSearchSkill(search_result(analysis_id, *items))
    provider = MockLLMProvider()
    app.dependency_overrides[require_question_ready_analysis] = ready_analysis
    app.dependency_overrides[get_search_repository_skill] = lambda: search
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return search, provider


async def test_valid_question_returns_grounded_citation(
    client: AsyncClient, test_app: FastAPI
) -> None:
    analysis_id = uuid4()
    item = evidence()
    search, provider = configure_runtime(test_app, analysis_id, item)
    response = await client.post(
        f"/api/v1/analyses/{analysis_id}/questions",
        json={
            "question": "Where is authentication implemented?",
            "language_filters": [" Python "],
            "path_prefix": "app/",
            "retrieval_limit": 8,
            "retrieval_minimum_score": 0.1,
            "maximum_citations": 5,
        },
        headers={"x-correlation-id": "40b2c9d3-f9c4-466b-a59d-789c84ed88dd"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_job_id"] == str(analysis_id)
    assert payload["citations"] == [
        {
            "chunk_id": item.chunk_id,
            "repository_file_id": str(item.repository_file_id),
            "path": item.path,
            "start_line": item.start_line,
            "end_line": item.end_line,
            "content_hash": item.content_hash,
        }
    ]
    assert payload["provider"] == "mock"
    assert payload["correlation_id"] == "40b2c9d3-f9c4-466b-a59d-789c84ed88dd"
    assert "chain_of_thought" not in payload
    assert "raw_provider_response" not in payload
    assert len(provider.requests) == 1
    forwarded = search.requests[0]
    assert forwarded.analysis_job_id == analysis_id
    assert forwarded.languages == ("python",)
    assert forwarded.path_prefix == "app/"


async def test_insufficient_evidence_returns_200_without_provider(
    client: AsyncClient, test_app: FastAPI
) -> None:
    analysis_id = uuid4()
    _search, provider = configure_runtime(test_app, analysis_id)
    response = await client.post(
        f"/api/v1/analyses/{analysis_id}/questions",
        json={"question": "Unknown behavior?"},
    )
    assert response.status_code == 200
    assert response.json()["insufficient_evidence"] is True
    assert response.json()["citations"] == []
    assert response.json()["provider"] is None
    assert provider.requests == []


@pytest.mark.parametrize(
    "body",
    [
        {"question": "   "},
        {"question": "x" * 4001},
        {"question": "valid", "retrieval_limit": 0},
        {"question": "valid", "retrieval_minimum_score": 111},
        {"question": "valid", "maximum_citations": 0},
    ],
)
async def test_invalid_question_requests_use_stable_error(
    client: AsyncClient, test_app: FastAPI, body: dict[str, object]
) -> None:
    analysis_id = uuid4()
    configure_runtime(test_app, analysis_id, evidence())
    response = await client.post(f"/api/v1/analyses/{analysis_id}/questions", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "repository_question_invalid"


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (AnalysisNotFoundError(), 404, "analysis_not_found"),
        (AnalysisNotReadyError(), 409, "analysis_not_ready"),
    ],
)
async def test_analysis_readiness_errors(
    client: AsyncClient,
    test_app: FastAPI,
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    async def unavailable_analysis(analysis_id: UUID) -> AnalysisJob:
        raise error

    test_app.dependency_overrides[require_question_ready_analysis] = unavailable_analysis
    test_app.dependency_overrides[get_repository_intelligence_agent] = lambda: object()
    response = await client.post(
        f"/api/v1/analyses/{uuid4()}/questions", json={"question": "question"}
    )
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


class FailingAgent:
    async def run(self, request: RepositoryAgentRequest) -> RepositoryAgentResponse:
        raise RepositoryAgentSearchFailedError


async def test_agent_failure_is_translated_without_raw_details(
    client: AsyncClient, test_app: FastAPI
) -> None:
    test_app.dependency_overrides[require_question_ready_analysis] = ready_analysis
    test_app.dependency_overrides[get_repository_intelligence_agent] = FailingAgent
    response = await client.post(
        f"/api/v1/analyses/{uuid4()}/questions", json={"question": "question"}
    )
    assert response.status_code == 502
    payload = response.json()
    assert payload["error"]["code"] == "repository_question_failed"
    assert "search" not in payload["error"]["message"].lower()


def test_public_response_schema_has_no_internal_fields() -> None:
    fields = RepositoryAgentResponse.model_fields
    assert "chain_of_thought" not in fields
    assert "raw_provider_response" not in fields
    assert "prompt" not in fields
    citation_fields = RepositoryAgentCitation.model_fields
    assert "temporary_path" not in citation_fields
    assert EvidenceQuality.HIGH.value == "high"


class FakeJobs:
    def __init__(self, job: AnalysisJob | None) -> None:
        self.job = job

    async def get_by_id(self, analysis_id: UUID) -> AnalysisJob | None:
        return self.job


class FakeParsed:
    def __init__(self, has_chunks: bool) -> None:
        self._has_chunks = has_chunks

    async def has_chunks(self, analysis_id: UUID) -> bool:
        return self._has_chunks


@pytest.mark.parametrize("status", [AnalysisJobStatus.FAILED, AnalysisJobStatus.CANCELLED])
async def test_failed_and_cancelled_analysis_are_not_ready(status: AnalysisJobStatus) -> None:
    analysis_id = uuid4()
    job = AnalysisJob(
        id=analysis_id,
        repository_id=uuid4(),
        pipeline_version="1",
        status=status,
    )
    with pytest.raises(AnalysisNotReadyError):
        await require_question_ready_analysis(
            analysis_id,
            cast(AnalysisJobRepository, FakeJobs(job)),
            cast(ParsedRepository, FakeParsed(True)),
        )


@pytest.mark.parametrize("status", [AnalysisJobStatus.RUNNING, AnalysisJobStatus.COMPLETED])
async def test_running_and_completed_analysis_require_parsed_chunks(
    status: AnalysisJobStatus,
) -> None:
    analysis_id = uuid4()
    job = AnalysisJob(
        id=analysis_id,
        repository_id=uuid4(),
        pipeline_version="1",
        status=status,
    )
    with pytest.raises(AnalysisNotReadyError):
        await require_question_ready_analysis(
            analysis_id,
            cast(AnalysisJobRepository, FakeJobs(job)),
            cast(ParsedRepository, FakeParsed(False)),
        )
