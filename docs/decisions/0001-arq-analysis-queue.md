# ADR 0001: ARQ for minimal analysis dispatch

## Status

Accepted for the repository-ingestion worker milestone.

## Decision

Use ARQ as the Redis-backed queue adapter behind the internal `AnalysisQueue` protocol. Keep the worker entrypoint in the shared API Python package so it can reuse the existing typed persistence and ingestion services without introducing a second package.

## Consequences

The API depends only on the queue protocol, unit tests use fakes without Redis, and the real worker is started with `arq app.worker.WorkerSettings`. ARQ supplies bounded concurrency, timeouts, Redis delivery, and worker health checks with substantially less machinery than Celery. Durable database state remains authoritative; completed stages make duplicate deliveries no-ops.
