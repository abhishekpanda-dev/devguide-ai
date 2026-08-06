from typing import Protocol
from uuid import UUID

from arq.connections import ArqRedis, RedisSettings, create_pool

from app.core.exceptions import RedisUnavailableError


class AnalysisQueue(Protocol):
    async def enqueue_analysis(
        self, analysis_job_id: UUID, *, deduplication_key: str | None = None
    ) -> None: ...


class ArqAnalysisQueue:
    def __init__(
        self, *, redis_url: str, queue_name: str, retry_count: int, retry_delay_seconds: int
    ) -> None:
        self._redis_settings = RedisSettings.from_dsn(redis_url)
        self._redis_settings.conn_retries = retry_count
        self._redis_settings.conn_retry_delay = retry_delay_seconds
        self._pool: ArqRedis | None = None
        self._queue_name = queue_name

    async def enqueue_analysis(
        self, analysis_job_id: UUID, *, deduplication_key: str | None = None
    ) -> None:
        try:
            if self._pool is None:
                self._pool = await create_pool(self._redis_settings)
            job = await self._pool.enqueue_job(
                "process_analysis",
                str(analysis_job_id),
                _job_id=deduplication_key,
                _queue_name=self._queue_name,
            )
        except Exception as exc:
            raise RedisUnavailableError from exc
        if job is None:
            return

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()


def create_analysis_queue(
    redis_url: str, queue_name: str, retry_count: int, retry_delay_seconds: int
) -> ArqAnalysisQueue:
    return ArqAnalysisQueue(
        redis_url=redis_url,
        queue_name=queue_name,
        retry_count=retry_count,
        retry_delay_seconds=retry_delay_seconds,
    )
