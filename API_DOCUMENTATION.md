# API Documentation

## Status

The FastAPI, persistence, and repository-submission foundations are implemented under `apps/api`. Submission creates database records only: it does not clone a repository, contact GitHub, enqueue a worker, or start analysis. Reports, chat, and AI functionality remain unimplemented.

Secure shallow-clone primitives now exist as an internal service for future worker use. They are not exposed as a public endpoint, and repository submission still does not trigger ingestion. Temporary clones are bounded, repository code is never executed, and workspaces are deleted after processing.

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

## `POST /api/v1/repositories`

Accepts `{"source_url":"https://github.com/owner/repository"}` and returns `201` with `repository` and queued `analysis_job` objects. Only public `https://github.com/{owner}/{repository}` URLs are accepted. A trailing slash and `.git` suffix are removed during normalization. Credentials, ports, other schemes or hosts, IP addresses, query strings, fragments, traversal, and extra path segments are rejected.

An existing normalized repository is reused, while every accepted submission creates a new queued analysis job using the configured pipeline version. This endpoint performs no network request and triggers no clone or worker.

## `GET /api/v1/repositories/{repository_id}`

Returns a repository record or `repository_not_found` with `404`.

## `GET /api/v1/analyses/{analysis_id}`

Returns an analysis-job status record or `analysis_not_found` with `404`.

## `GET /api/v1/repositories/{repository_id}/analyses`

Returns `{items, limit, offset}` for the repository. `limit` is between 1 and 100; `offset` is non-negative.

## Unresolved contract work

Authentication, rate limits, idempotency beyond repository reuse, retention, worker dispatch, and full asynchronous lifecycle semantics remain undecided.
