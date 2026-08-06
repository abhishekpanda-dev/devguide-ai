from typing import Any, ClassVar
from uuid import UUID

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.repositories import AnalysisJobRepository, RepositoryRepository
from app.services.ingestion import RepositoryIngestionService
from app.services.worker import AnalysisWorkerService


async def process_analysis(ctx: dict[str, Any], analysis_job_id: str) -> dict[str, Any]:
    settings = ctx["settings"]
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        ingestion = RepositoryIngestionService(
            session=session,
            repositories=RepositoryRepository(session),
            analysis_jobs=AnalysisJobRepository(session),
            settings=settings,
        )
        result = await AnalysisWorkerService(session=session, ingestion=ingestion).process(
            UUID(analysis_job_id)
        )
        return {
            "analysis_job_id": str(result.analysis_job_id),
            "stage_name": result.stage_name,
            "stage_status": result.stage_status.value,
            "analysis_status": result.analysis_status.value,
            "attempt": result.attempt,
            "progress_percent": result.progress_percent,
            "error_code": result.error_code,
            "limitations": list(result.limitations),
        }


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    ctx["settings"] = settings
    ctx["session_factory"] = create_session_factory(settings)


class WorkerSettings:
    settings = get_settings()
    configured_redis = RedisSettings.from_dsn(str(settings.redis_url))
    configured_redis.conn_retries = settings.worker_retry_count
    configured_redis.conn_retry_delay = settings.worker_retry_delay_seconds
    functions: ClassVar[list[Any]] = [process_analysis]
    on_startup = startup
    redis_settings = configured_redis
    queue_name = settings.queue_name
    max_jobs = settings.worker_concurrency
    job_timeout = settings.worker_job_timeout_seconds
    max_tries = settings.worker_retry_count + 1
    retry_jobs = True
    health_check_interval = settings.worker_heartbeat_interval_seconds
