import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, DuplicateEmailError
from app.models.auth import AuthSession, User

_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    salt_text = base64.urlsafe_b64encode(salt).decode()
    digest_text = base64.urlsafe_b64encode(digest).decode()
    return f"pbkdf2_sha256${_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.urlsafe_b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession, session_hours: int) -> None:
        self._session = session
        self._session_hours = session_hours

    async def register(self, email: str, password: str) -> User:
        user = User(email=email.strip().lower(), password_hash=hash_password(password))
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateEmailError from exc
        await self._session.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError
        return user

    async def create_session(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        self._session.add(
            AuthSession(
                user_id=user.id,
                token_hash=token_digest(token),
                expires_at=datetime.now(UTC) + timedelta(hours=self._session_hours),
            )
        )
        await self._session.commit()
        return token

    async def resolve_session(self, token: str | None) -> User | None:
        if not token:
            return None
        statement = (
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == token_digest(token),
                AuthSession.expires_at > datetime.now(UTC),
            )
        )
        result: User | None = await self._session.scalar(statement)
        return result

    async def logout(self, token: str | None) -> None:
        if token:
            await self._session.execute(
                delete(AuthSession).where(AuthSession.token_hash == token_digest(token))
            )
            await self._session.commit()
