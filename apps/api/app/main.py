from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.db.session import create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    application = FastAPI(
        title="DevGuide AI API",
        version=resolved_settings.app_version,
        docs_url="/docs" if resolved_settings.environment != "production" else None,
        redoc_url=None,
    )
    application.state.settings = resolved_settings
    application.state.session_factory = create_session_factory(resolved_settings)
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(v1_router, prefix="/api/v1")
    return application


app = create_app()
