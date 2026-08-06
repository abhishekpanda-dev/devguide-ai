from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.db.session import create_session_factory
from app.queue import create_analysis_queue


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.analysis_queue = create_analysis_queue(
            str(resolved_settings.redis_url),
            resolved_settings.queue_name,
            resolved_settings.worker_retry_count,
            resolved_settings.worker_retry_delay_seconds,
        )
        try:
            yield
        finally:
            await application.state.analysis_queue.close()

    configure_logging(resolved_settings.log_level)
    application = FastAPI(
        title="DevGuide AI API",
        version=resolved_settings.app_version,
        docs_url="/docs" if resolved_settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.session_factory = create_session_factory(resolved_settings)
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(v1_router, prefix="/api/v1")
    return application


app = create_app()
