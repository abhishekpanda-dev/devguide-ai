import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.middleware import correlation_id_context

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ReadinessError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="service_unavailable",
            message="A required service dependency is unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _response(*, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id_context.get(),
            }
        },
    )


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    logger.warning("application_error", extra={"error_code": exc.code})
    return _response(code=exc.code, message=exc.message, status_code=exc.status_code)


async def validation_error_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return _response(
        code="validation_error",
        message="The request is invalid.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=exc)
    return _response(
        code="internal_server_error",
        message="An unexpected error occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unexpected_error_handler)
