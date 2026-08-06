from contextvars import ContextVar
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_ID_HEADER = "x-correlation-id"
correlation_id_context: ContextVar[str] = ContextVar("correlation_id", default="unavailable")


def _safe_correlation_id(value: str | None) -> str:
    if value is None or len(value) > 36:
        return str(uuid4())
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        return str(uuid4())


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        supplied = headers.get(CORRELATION_ID_HEADER.encode())
        correlation_id = _safe_correlation_id(
            supplied.decode("ascii", errors="ignore") if supplied else None
        )
        token = correlation_id_context.set(correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((CORRELATION_ID_HEADER.encode(), correlation_id.encode()))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            correlation_id_context.reset(token)
