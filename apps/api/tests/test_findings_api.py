from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import get_code_finding_service
from app.core.exceptions import AnalysisNotFoundError, AnalysisNotReadyError
from app.models import FindingCategory, FindingSeverity
from app.schemas import CodeFindingsResponse


class FakeService:
    def __init__(self) -> None:
        self.filters: tuple[object, ...] | None = None

    async def list_required(
        self,
        analysis_job_id: UUID,
        *,
        severity: FindingSeverity | None,
        category: FindingCategory | None,
        path_prefix: str | None,
        limit: int,
    ) -> CodeFindingsResponse:
        self.filters = (severity, category, path_prefix, limit)
        return CodeFindingsResponse(
            analysis_job_id=analysis_job_id,
            total_count=1,
            returned_count=1,
            severity_counts={"high": 1, "warning": 0, "info": 0},
            limitations=[],
            findings=[
                {
                    "id": uuid4(),
                    "rule_id": "python.eval",
                    "severity": "high",
                    "category": "security",
                    "title": "Potential eval() execution",
                    "explanation": "Review recommended.",
                    "path": "src/app.py",
                    "start_line": 4,
                    "end_line": 4,
                    "evidence_excerpt": "eval(value)",
                    "deterministic_recommendation": "Use explicit parsing.",
                    "confidence": 0.99,
                    "content_hash": "a" * 64,
                    "commit_sha": "b" * 40,
                    "source_url": f"https://github.com/acme/project/blob/{'b' * 40}/src/app.py#L4",
                }
            ],
        )


class MissingService:
    async def list_required(self, analysis_job_id: UUID, **kwargs: object) -> CodeFindingsResponse:
        raise AnalysisNotFoundError


class NotReadyService:
    async def list_required(self, analysis_job_id: UUID, **kwargs: object) -> CodeFindingsResponse:
        raise AnalysisNotReadyError


async def test_findings_endpoint_and_filters(client: AsyncClient, test_app: FastAPI) -> None:
    service = FakeService()
    test_app.dependency_overrides[get_code_finding_service] = lambda: service
    analysis_id = uuid4()
    response = await client.get(
        f"/api/v1/analyses/{analysis_id}/findings?severity=high&category=security&path_prefix=src/&limit=10"
    )
    assert response.status_code == 200
    assert response.json()["findings"][0]["source_url"].endswith("src/app.py#L4")
    assert service.filters == (FindingSeverity.HIGH, FindingCategory.SECURITY, "src/", 10)


@pytest.mark.parametrize(
    ("dependency", "status", "code"),
    [(MissingService, 404, "analysis_not_found"), (NotReadyService, 409, "analysis_not_ready")],
)
async def test_findings_endpoint_errors(
    client: AsyncClient,
    test_app: FastAPI,
    dependency: type[MissingService] | type[NotReadyService],
    status: int,
    code: str,
) -> None:
    test_app.dependency_overrides[get_code_finding_service] = dependency
    response = await client.get(f"/api/v1/analyses/{uuid4()}/findings")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


async def test_findings_invalid_filter(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/analyses/{uuid4()}/findings?severity=critical")
    assert response.status_code == 422
