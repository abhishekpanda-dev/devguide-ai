from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_access_control_service, get_current_user
from app.core.config import Settings
from app.main import create_app
from app.models import User


@pytest.fixture
def test_settings() -> Settings:
    return Settings(environment="test", ai_provider_name="mock")


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    app = create_app(test_settings)
    app.dependency_overrides[get_current_user] = lambda: User(
        id=uuid4(), email="test@example.com", password_hash="not-used"
    )

    class AllowAllAccess:
        async def grant_repository(self, _user_id: object, _repository_id: object) -> None:
            pass

        async def ensure_repository(self, _user_id: object, _repository_id: object) -> None:
            pass

        async def ensure_analysis(self, _user_id: object, _analysis_id: object) -> None:
            pass

    app.dependency_overrides[get_access_control_service] = AllowAllAccess
    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as value:
        yield value
