from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import ValidationError

from app.api.dependencies import get_structure_service
from app.core.exceptions import AnalysisNotFoundError, AnalysisNotReadyError
from app.schemas.structure import StructureEdgeRead, StructureResponse


class FakeStructureService:
    def __init__(self) -> None:
        self.filters: tuple[object, ...] | None = None

    async def get_required(self, analysis_id: UUID, **filters: object) -> StructureResponse:
        self.filters = tuple(filters.values())
        file_id = uuid4()
        file = {
            "repository_file_id": file_id,
            "path": "src/main.ts",
            "language": "typescript",
            "classification": "source",
            "line_count": 2,
            "content_hash": "a" * 64,
            "commit_sha": "b" * 40,
            "is_entry_point": True,
            "entry_point_reason": "package.json main field.",
            "entry_point_confidence": 1,
            "inbound_dependency_count": 0,
            "outbound_dependency_count": 0,
            "total_dependency_count": 0,
        }
        return StructureResponse(
            analysis_job_id=analysis_id,
            repository={"id": uuid4(), "owner": "acme", "name": "project", "commit_sha": "b" * 40},
            files=[file],
            dependency_edges=[],
            entry_points=[file],
            summary={
                "file_count": 1,
                "directory_count": 1,
                "language_counts": {"typescript": 1},
                "edge_count": 0,
                "entry_point_count": 1,
                "highest_inbound_files": [file],
                "highest_outbound_files": [file],
                "most_connected_files": [file],
            },
            limitations=[],
        )


class MissingStructureService:
    async def get_required(self, analysis_id: UUID, **filters: object) -> StructureResponse:
        raise AnalysisNotFoundError


class NotReadyStructureService:
    async def get_required(self, analysis_id: UUID, **filters: object) -> StructureResponse:
        raise AnalysisNotReadyError


async def test_structure_endpoint_filters_and_empty_edges(
    client: AsyncClient, test_app: FastAPI
) -> None:
    service = FakeStructureService()
    test_app.dependency_overrides[get_structure_service] = lambda: service
    response = await client.get(
        f"/api/v1/analyses/{uuid4()}/structure?language=typescript&path_prefix=src&relationship_type=imports&limit=20"
    )
    assert response.status_code == 200
    assert response.json()["dependency_edges"] == []
    assert response.json()["entry_points"][0]["path"] == "src/main.ts"
    assert service.filters == ("typescript", "src", "imports", 20)


async def test_structure_endpoint_safe_errors_and_invalid_filter(
    client: AsyncClient, test_app: FastAPI
) -> None:
    for service, status, code in (
        (MissingStructureService(), 404, "analysis_not_found"),
        (NotReadyStructureService(), 409, "analysis_not_ready"),
    ):
        test_app.dependency_overrides[get_structure_service] = lambda service=service: service
        response = await client.get(f"/api/v1/analyses/{uuid4()}/structure")
        assert response.status_code == status and response.json()["error"]["code"] == code
    response = await client.get(f"/api/v1/analyses/{uuid4()}/structure?relationship_type=dynamic")
    assert response.status_code == 422


def test_structure_edge_rejects_unsafe_paths_and_lines() -> None:
    with pytest.raises(ValidationError):
        StructureEdgeRead(
            id=uuid4(),
            source_repository_file_id=uuid4(),
            target_repository_file_id=uuid4(),
            relationship_type="imports",
            module_name="x",
            source_path="../outside.py",
            target_path="inside.py",
            source_line=0,
            confidence=1,
            source_url="https://github.com/acme/project/blob/commit/inside.py#L1",
        )
