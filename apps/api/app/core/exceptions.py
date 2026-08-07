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


class ResourceNotFoundError(AppError):
    def __init__(self, resource: str) -> None:
        super().__init__(
            code="resource_not_found",
            message=f"{resource} was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ResourceConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="resource_conflict",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


class PersistenceError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="persistence_error",
            message="The requested data operation could not be completed.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ApplicationValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="validation_error",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class InvalidRepositoryUrlError(AppError):
    def __init__(self, message: str = "The repository URL is invalid or unsupported.") -> None:
        super().__init__(
            code="invalid_repository_url",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class RepositoryNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_not_found",
            message="The repository was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AnalysisNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="analysis_not_found",
            message="The analysis was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AnalysisDispatchFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="analysis_dispatch_failed",
            message="The analysis was saved but could not be dispatched.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class RedisUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="redis_unavailable",
            message="The analysis queue is unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class RepositoryCloneFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_clone_failed",
            message="The public repository could not be cloned.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class RepositoryCloneTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_clone_timeout",
            message="The repository clone operation timed out.",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )


class RepositoryLimitExceededError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="repository_limit_exceeded",
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class RepositoryWorkspaceError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_workspace_error",
            message="The temporary repository workspace could not be managed safely.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class InvalidRepositorySourceError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="invalid_repository_source",
            message="The repository source is invalid or unsupported for ingestion.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class GitNotAvailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="git_not_available",
            message="Git is not available to the ingestion service.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class AIProviderNotConfiguredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="ai_provider_not_configured",
            message="The configured AI provider is not available.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class AIProviderUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="ai_provider_unavailable",
            message="The AI provider is temporarily unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class AIProviderTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="ai_provider_timeout",
            message="The AI provider request timed out.",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )


class AIResponseInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="ai_response_invalid",
            message="The AI provider returned an invalid response.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class GroundedAnswerValidationError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="grounded_answer_validation_failed",
            message="The generated answer could not be validated against repository evidence.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class RepositoryAgentInvalidRequestError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_agent_invalid_request",
            message="The repository agent request is invalid.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class RepositoryAgentSearchFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_agent_search_failed",
            message="Repository evidence search could not be completed.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class RepositoryAgentEvidenceInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_agent_evidence_invalid",
            message="Repository evidence failed agent validation.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class RepositoryAgentAnswerFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_agent_answer_failed",
            message="The grounded repository answer could not be completed.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class AnalysisNotReadyError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="analysis_not_ready",
            message="The analysis is not ready for repository questions.",
            status_code=status.HTTP_409_CONFLICT,
        )


class RepositoryQuestionInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_question_invalid",
            message="The repository question request is invalid.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class RepositoryQuestionFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="repository_question_failed",
            message="The repository question could not be completed.",
            status_code=status.HTTP_502_BAD_GATEWAY,
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


async def validation_error_handler(request: Request, _exc: RequestValidationError) -> JSONResponse:
    if request.url.path.endswith("/questions"):
        error = RepositoryQuestionInvalidError()
        return _response(code=error.code, message=error.message, status_code=error.status_code)
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
