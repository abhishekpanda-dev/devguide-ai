from httpx import AsyncClient


async def test_permitted_origin_receives_cors_headers(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["vary"] == "Origin"


async def test_options_preflight_succeeds_for_required_method_and_headers(
    client: AsyncClient,
) -> None:
    response = await client.options(
        "/api/v1/repositories",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-correlation-id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert response.headers["access-control-allow-methods"] == "GET, POST"
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "content-type" in allowed_headers
    assert "x-correlation-id" in allowed_headers


async def test_unapproved_origin_receives_no_allow_origin_header(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "https://unapproved.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
