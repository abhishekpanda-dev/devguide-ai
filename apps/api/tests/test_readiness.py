from httpx import AsyncClient

from app.api.dependencies import get_readiness_service
from app.core.exceptions import ReadinessError
from app.schemas.health import HealthResponse


class PassingReadinessService:
    async def ensure_ready(self) -> None:
        return None

    def get_status(self) -> HealthResponse:
        return HealthResponse(version="0.1.0")


class FailingReadinessService(PassingReadinessService):
    async def ensure_ready(self) -> None:
        raise ReadinessError


async def test_readiness_returns_200_when_checks_pass(client: AsyncClient) -> None:
    client._transport.app.dependency_overrides[get_readiness_service] = PassingReadinessService  # type: ignore[attr-defined]
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_returns_503_when_checks_fail(client: AsyncClient) -> None:
    client._transport.app.dependency_overrides[get_readiness_service] = FailingReadinessService  # type: ignore[attr-defined]
    response = await client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
