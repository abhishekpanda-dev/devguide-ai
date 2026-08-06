from uuid import UUID, uuid4

from httpx import AsyncClient

from app.schemas.health import HealthResponse


async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_health_response_matches_schema(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    parsed = HealthResponse.model_validate(response.json())
    assert parsed.model_dump() == {"status": "ok", "service": "devguide-api", "version": "0.1.0"}


async def test_correlation_id_is_returned(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    UUID(response.headers["x-correlation-id"])


async def test_valid_request_correlation_id_is_preserved(client: AsyncClient) -> None:
    correlation_id = str(uuid4())
    response = await client.get("/api/v1/health", headers={"x-correlation-id": correlation_id})
    assert response.headers["x-correlation-id"] == correlation_id


async def test_invalid_request_correlation_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"x-correlation-id": "not-a-safe-id"})
    replacement = response.headers["x-correlation-id"]
    assert replacement != "not-a-safe-id"
    UUID(replacement)
