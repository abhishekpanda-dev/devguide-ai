from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import (
    AnalysisNotFoundError,
    AuthenticationError,
    DuplicateEmailError,
    RepositoryNotFoundError,
)
from app.db.base import Base
from app.models import AnalysisJob, Repository, RepositorySourceType, RepositoryStatus
from app.services.access import AccessControlService
from app.services.auth import AuthService, hash_password, verify_password


@pytest.fixture
async def auth_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("long-and-private-password")
    second = hash_password("long-and-private-password")
    assert first != second
    assert "long-and-private-password" not in first
    assert verify_password("long-and-private-password", first)
    assert not verify_password("wrong-password", first)


async def test_registration_login_session_and_logout(auth_session: AsyncSession) -> None:
    service = AuthService(auth_session, session_hours=1)
    user = await service.register("Person@Example.com", "long-and-private-password")
    assert user.email == "person@example.com"
    assert user.password_hash != "long-and-private-password"
    assert (await service.authenticate(user.email, "long-and-private-password")).id == user.id
    token = await service.create_session(user)
    assert await service.resolve_session(token) is not None
    await service.logout(token)
    assert await service.resolve_session(token) is None


async def test_auth_errors_do_not_disclose_account_existence(auth_session: AsyncSession) -> None:
    service = AuthService(auth_session, session_hours=1)
    await service.register("person@example.com", "long-and-private-password")
    with pytest.raises(DuplicateEmailError) as duplicate:
        await service.register("PERSON@example.com", "another-private-password")
    assert "person@example.com" not in duplicate.value.message
    with pytest.raises(AuthenticationError) as missing:
        await service.authenticate("missing@example.com", "wrong-password")
    with pytest.raises(AuthenticationError) as incorrect:
        await service.authenticate("person@example.com", "wrong-password")
    assert missing.value.message == incorrect.value.message == "Email or password is incorrect."


async def test_repository_access_is_isolated_between_users(auth_session: AsyncSession) -> None:
    auth = AuthService(auth_session, session_hours=1)
    owner = await auth.register("owner@example.com", "long-and-private-password")
    stranger = await auth.register("stranger@example.com", "long-and-private-password")
    repository = Repository(
        source_type=RepositorySourceType.GITHUB_PUBLIC,
        source_url="https://github.com/acme/project",
        normalized_url="https://github.com/acme/project",
        owner="acme",
        name="project",
        status=RepositoryStatus.PENDING,
    )
    auth_session.add(repository)
    await auth_session.flush()
    analysis = AnalysisJob(repository_id=repository.id, pipeline_version="1")
    auth_session.add(analysis)
    await auth_session.commit()
    access = AccessControlService(auth_session)
    await access.grant_repository(owner.id, repository.id)
    await access.ensure_repository(owner.id, repository.id)
    await access.ensure_analysis(owner.id, analysis.id)
    with pytest.raises(RepositoryNotFoundError):
        await access.ensure_repository(stranger.id, repository.id)
    with pytest.raises(AnalysisNotFoundError):
        await access.ensure_analysis(stranger.id, analysis.id)
