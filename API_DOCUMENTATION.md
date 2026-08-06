# API Documentation

## Status

The FastAPI and initial database foundations are implemented under `apps/api`. Only liveness and readiness are available. Repository, analysis-job, and analysis-stage persistence models are internal and have no public API routes. Repository ingestion, reports, chat, and AI functionality remain unimplemented.

## Common behavior

The API is versioned under `/api/v1`. Every HTTP response includes `X-Correlation-ID`. Clients may supply a UUID in that header; invalid values are replaced.

Errors use this envelope:

```json
{"error":{"code":"string","message":"string","correlation_id":"string"}}
```

## `GET /api/v1/health`

Returns `200` when the API process can serve requests. It does not test external dependencies.

```json
{"status":"ok","service":"devguide-api","version":"0.1.0"}
```

## `GET /api/v1/ready`

Uses the readiness service to check required dependencies. The current implementation executes a lightweight PostgreSQL query. It returns the health schema with `200` when ready, or a centralized `service_unavailable` error with `503` when the database check fails.

## Unresolved contract work

Authentication, resource identifiers, asynchronous job semantics, pagination, rate limits, idempotency, and retention remain undecided. No endpoints for those planned capabilities are exposed.
