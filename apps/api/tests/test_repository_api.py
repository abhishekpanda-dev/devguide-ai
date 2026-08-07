from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import (
    get_analysis_job_service,
    get_analysis_summary_service,
    get_repository_service,
    get_submission_service,
)
from app.core.exceptions import (
    AnalysisNotFoundError,
    AnalysisSummaryNotReadyError,
    RepositoryNotFoundError,
)
from app.models import (
    AnalysisJob,
    AnalysisJobStatus,
    Repository,
    RepositorySourceType,
    RepositoryStatus,
)
from app.schemas import AnalysisSummary
from app.services.repository_url import normalize_repository_url
from app.services.submission import RepositorySubmissionResult


def records() -> tuple[Repository, AnalysisJob]:
    now = datetime.now(UTC)
    repository = Repository(
        id=uuid4(),
        source_url="https://github.com/acme/project",
        normalized_url="https://github.com/acme/project",
        owner="acme",
        name="project",
        source_type=RepositorySourceType.GITHUB_PUBLIC,
        default_branch=None,
        latest_commit_sha=None,
        status=RepositoryStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    analysis = AnalysisJob(
        id=uuid4(),
        repository_id=repository.id,
        status=AnalysisJobStatus.QUEUED,
        current_stage=None,
        progress_percent=0,
        pipeline_version="1",
        error_code=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    return repository, analysis


class FakeSubmissionService:
    def __init__(self, repository: Repository, analysis: AnalysisJob) -> None:
        self._result = RepositorySubmissionResult(repository, analysis)

    async def submit(self, source_url: str) -> RepositorySubmissionResult:
        assert source_url == "https://github.com/acme/project"
        return self._result


class ValidatingSubmissionService:
    async def submit(self, source_url: str) -> RepositorySubmissionResult:
        normalize_repository_url(source_url)
        raise AssertionError("invalid input unexpectedly passed validation")


class FakeRepositoryService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def get_required(self, repository_id: UUID) -> Repository:
        assert repository_id == self._repository.id
        return self._repository


class MissingRepositoryService:
    async def get_required(self, repository_id: UUID) -> Repository:
        raise RepositoryNotFoundError


class FakeAnalysisService:
    def __init__(self, analysis: AnalysisJob) -> None:
        self._analysis = analysis
        self.pagination: tuple[int, int] | None = None

    async def get_required(self, analysis_id: UUID) -> AnalysisJob:
        assert analysis_id == self._analysis.id
        return self._analysis

    async def list_for_repository(
        self, repository_id: UUID, *, limit: int, offset: int
    ) -> list[AnalysisJob]:
        assert repository_id == self._analysis.repository_id
        self.pagination = (limit, offset)
        return [self._analysis]


class MissingAnalysisService:
    async def get_required(self, analysis_id: UUID) -> AnalysisJob:
        raise AnalysisNotFoundError


class FakeAnalysisSummaryService:
    async def get_required(self, analysis_id: UUID) -> AnalysisSummary:
        return AnalysisSummary(
            analysis_job_id=analysis_id,
            files_analyzed=2,
            chunks_created=3,
            languages=[{"language": "python", "file_count": 2, "line_count": 10}],
            total_lines=10,
            test_file_count=1,
            documentation_file_count=0,
            skipped_file_count=1,
            limitations=["one file was skipped"],
        )


class MissingAnalysisSummaryService:
    async def get_required(self, analysis_id: UUID) -> AnalysisSummary:
        raise AnalysisNotFoundError


class NotReadyAnalysisSummaryService:
    async def get_required(self, analysis_id: UUID) -> AnalysisSummary:
        raise AnalysisSummaryNotReadyError


async def test_post_repository_returns_201_documented_response(
    client: AsyncClient, test_app: FastAPI
) -> None:
    repository, analysis = records()
    test_app.dependency_overrides[get_submission_service] = lambda: FakeSubmissionService(
        repository, analysis
    )

    response = await client.post(
        "/api/v1/repositories",
        json={"source_url": "https://github.com/acme/project"},
        headers={"x-correlation-id": "40b2c9d3-f9c4-466b-a59d-789c84ed88dd"},
    )

    assert response.status_code == 201
    assert response.json()["repository"]["id"] == str(repository.id)
    assert response.json()["analysis_job"]["id"] == str(analysis.id)
    assert response.json()["analysis_job"]["status"] == "queued"
    assert response.headers["x-correlation-id"] == "40b2c9d3-f9c4-466b-a59d-789c84ed88dd"


async def test_post_invalid_repository_url_uses_documented_error(
    client: AsyncClient, test_app: FastAPI
) -> None:
    test_app.dependency_overrides[get_submission_service] = ValidatingSubmissionService
    response = await client.post(
        "/api/v1/repositories",
        json={"source_url": "http://github.com/acme/project"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_repository_url"
    UUID(response.json()["error"]["correlation_id"])


async def test_get_repository_returns_200(client: AsyncClient, test_app: FastAPI) -> None:
    repository, _analysis = records()
    test_app.dependency_overrides[get_repository_service] = lambda: FakeRepositoryService(
        repository
    )
    response = await client.get(f"/api/v1/repositories/{repository.id}")
    assert response.status_code == 200
    assert response.json()["normalized_url"] == repository.normalized_url


async def test_get_missing_repository_returns_404_with_correlation_id(
    client: AsyncClient, test_app: FastAPI
) -> None:
    test_app.dependency_overrides[get_repository_service] = MissingRepositoryService
    correlation_id = "68d4c649-2a62-43d1-b40c-4991a467777b"
    response = await client.get(
        f"/api/v1/repositories/{uuid4()}", headers={"x-correlation-id": correlation_id}
    )
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "repository_not_found",
        "message": "The repository was not found.",
        "correlation_id": correlation_id,
    }


async def test_get_analysis_returns_200(client: AsyncClient, test_app: FastAPI) -> None:
    _repository, analysis = records()
    test_app.dependency_overrides[get_analysis_job_service] = lambda: FakeAnalysisService(analysis)
    response = await client.get(f"/api/v1/analyses/{analysis.id}")
    assert response.status_code == 200
    assert response.json()["repository_id"] == str(analysis.repository_id)


async def test_get_completed_analysis_returns_ready_state(
    client: AsyncClient, test_app: FastAPI
) -> None:
    _repository, analysis = records()
    analysis.status = AnalysisJobStatus.COMPLETED
    analysis.current_stage = "ready"
    analysis.progress_percent = 100
    analysis.completed_at = datetime.now(UTC)
    test_app.dependency_overrides[get_analysis_job_service] = lambda: FakeAnalysisService(analysis)

    response = await client.get(f"/api/v1/analyses/{analysis.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["current_stage"] == "ready"
    assert response.json()["progress_percent"] == 100
    assert response.json()["completed_at"] is not None
    assert response.json()["error_code"] is None
    assert response.json()["error_message"] is None


async def test_get_missing_analysis_returns_404(client: AsyncClient, test_app: FastAPI) -> None:
    test_app.dependency_overrides[get_analysis_job_service] = MissingAnalysisService
    response = await client.get(f"/api/v1/analyses/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_not_found"


async def test_get_analysis_summary_returns_persisted_statistics(
    client: AsyncClient, test_app: FastAPI
) -> None:
    test_app.dependency_overrides[get_analysis_summary_service] = FakeAnalysisSummaryService
    response = await client.get(f"/api/v1/analyses/{uuid4()}/summary")

    assert response.status_code == 200
    assert response.json()["files_analyzed"] == 2
    assert response.json()["languages"] == [
        {"language": "python", "file_count": 2, "line_count": 10}
    ]


async def test_get_missing_analysis_summary_returns_404(
    client: AsyncClient, test_app: FastAPI
) -> None:
    test_app.dependency_overrides[get_analysis_summary_service] = MissingAnalysisSummaryService
    response = await client.get(f"/api/v1/analyses/{uuid4()}/summary")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_not_found"


async def test_get_analysis_summary_without_parser_data_returns_not_ready(
    client: AsyncClient, test_app: FastAPI
) -> None:
    test_app.dependency_overrides[get_analysis_summary_service] = NotReadyAnalysisSummaryService
    response = await client.get(f"/api/v1/analyses/{uuid4()}/summary")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_not_ready"


async def test_list_analyses_supports_limit_and_offset(
    client: AsyncClient, test_app: FastAPI
) -> None:
    repository, analysis = records()
    repository_service = FakeRepositoryService(repository)
    analysis_service = FakeAnalysisService(analysis)
    test_app.dependency_overrides[get_repository_service] = lambda: repository_service
    test_app.dependency_overrides[get_analysis_job_service] = lambda: analysis_service

    response = await client.get(f"/api/v1/repositories/{repository.id}/analyses?limit=5&offset=10")

    assert response.status_code == 200
    assert response.json()["limit"] == 5
    assert response.json()["offset"] == 10
    assert len(response.json()["items"]) == 1
    assert analysis_service.pagination == (5, 10)
