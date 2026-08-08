from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient

from app.api.dependencies import get_auth_service, get_current_user
from app.core.exceptions import AuthenticationError, DuplicateEmailError
from app.models import User


class FakeAuthService:
    def __init__(self) -> None:
        self.user = User(
            id=uuid4(),
            email="person@example.com",
            password_hash="never-returned",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.logged_out = False

    async def register(self, email: str, password: str) -> User:
        if email == "taken@example.com":
            raise DuplicateEmailError
        assert password == "long-and-private-password"
        return self.user

    async def authenticate(self, email: str, password: str) -> User:
        if email != self.user.email or password != "long-and-private-password":
            raise AuthenticationError
        return self.user

    async def create_session(self, user: User) -> str:
        assert user is self.user
        return "opaque-session-token"

    async def logout(self, token: str | None) -> None:
        self.logged_out = token == "opaque-session-token"


async def test_register_login_me_and_logout_use_http_only_cookie(
    client: AsyncClient, test_app: FastAPI
) -> None:
    service = FakeAuthService()
    test_app.dependency_overrides[get_auth_service] = lambda: service
    test_app.dependency_overrides[get_current_user] = lambda: service.user

    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "password": "long-and-private-password",
            "confirm_password": "long-and-private-password",
        },
    )
    assert registered.status_code == 201
    assert registered.json()["user"]["email"] == "person@example.com"
    assert "password" not in registered.text
    assert "HttpOnly" in registered.headers["set-cookie"]

    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "long-and-private-password"},
    )
    assert logged_in.status_code == 200
    assert "opaque-session-token" in logged_in.headers["set-cookie"]
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    assert service.logged_out


async def test_login_and_registration_errors_are_generic(
    client: AsyncClient, test_app: FastAPI
) -> None:
    service = FakeAuthService()
    test_app.dependency_overrides[get_auth_service] = lambda: service
    invalid = await client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["message"] == "Email or password is incorrect."
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "taken@example.com",
            "password": "long-and-private-password",
            "confirm_password": "long-and-private-password",
        },
    )
    assert duplicate.status_code == 409
    assert "taken@example.com" not in duplicate.text
