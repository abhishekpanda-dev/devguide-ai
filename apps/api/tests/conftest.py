from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(environment="test", ai_provider_name="mock")


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    return create_app(test_settings)


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as value:
        yield value
