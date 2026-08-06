from httpx import AsyncClient

from app.api.dependencies import get_health_service
from app.core.exceptions import AppError


class FailingHealthService:
    def get_health(self) -> None:
        raise AppError(code="test_error", message="Controlled failure.", status_code=409)


async def test_centralized_exception_handler_uses_documented_format(client: AsyncClient) -> None:
    client._transport.app.dependency_overrides[get_health_service] = FailingHealthService  # type: ignore[attr-defined]
    response = await client.get(
        "/api/v1/health", headers={"x-correlation-id": "40b2c9d3-f9c4-466b-a59d-789c84ed88dd"}
    )
    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "test_error",
            "message": "Controlled failure.",
            "correlation_id": "40b2c9d3-f9c4-466b-a59d-789c84ed88dd",
        }
    }
