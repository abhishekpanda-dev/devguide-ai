# DevGuide AI API

This directory contains the FastAPI foundation and a minimal ARQ analysis worker. Repository submission commits its records and dispatches the analysis ID to Redis. The worker safely claims queued work and runs only the `repository_ingestion` stage.

The internal ingestion service now supplies secure cloning primitives for an existing repository and analysis job. It is not exposed through a public endpoint and no background worker invokes it yet.

## Requirements

- Python 3.11+
- PostgreSQL for a successful readiness check (tests do not require it)
- Redis for real submission dispatch and worker execution (unit tests do not require it)

## Setup and run

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Run these commands from `apps/api`:

```bash
ruff format --check .
ruff check .
mypy app tests
pytest
alembic upgrade head --sql
python -c "from app.main import app; assert app.title == 'DevGuide AI API'"
```

Run the worker with `arq app.worker.WorkerSettings`. A successful ingestion leaves the overall analysis `running` at 20%; parsing, language detection, indexing, embeddings, and later analysis stages are not implemented.

## Internal parser foundation

`app.parser.RepositoryParser` deterministically reads an existing repository workspace and returns accepted source files, extension-based language identifiers, SHA-256 metadata, line-based chunks, and repository summary statistics. It is internal only and is not called by the API or worker. Supported inputs are Python, JavaScript, TypeScript, Java, HTML, CSS, JSON, YAML, Markdown, and TOML. Binary, unsupported, oversized, rejected-media/archive/executable files, ignored directories, and symbolic links are skipped.

Chunking defaults to 200 lines with 20 lines of overlap and preserves one-based inclusive ranges. After ingestion, the worker parses the same temporary workspace and replaces analysis-scoped `repository_files` and `code_chunks` rows before cleanup. Successful parsing leaves the analysis running at 40%. There are no public file or chunk routes.

The parser performs no AST extraction, framework detection, AI calls, embeddings, network access, or repository-code execution.

Configuration uses `DEVGUIDE_`-prefixed environment variables. See the repository `.env.example`. Never place production credentials in that file or logs.

## Endpoints

- `GET /api/v1/health` reports process liveness without contacting external services.
- `GET /api/v1/ready` verifies required dependencies through `ReadinessService`; the default implementation performs a PostgreSQL `SELECT 1` and returns `503` on failure.
- `POST /api/v1/repositories` validates a public GitHub HTTPS URL, reuses its repository record when present, and creates a new queued analysis job.
- `GET /api/v1/repositories/{repository_id}` returns stored repository status.
- `GET /api/v1/analyses/{analysis_id}` returns stored analysis-job status.
- `GET /api/v1/repositories/{repository_id}/analyses` lists analysis jobs with `limit` and `offset`.

Submission creates database records only. It does not contact GitHub, clone code, enqueue Redis work, or start a worker. Accepted URLs normalize to `https://github.com/{owner}/{repository}` after removing an optional trailing slash or `.git` suffix.

All responses include `X-Correlation-ID`. A valid UUID supplied in that header is preserved; other values are replaced. Error responses use the documented centralized envelope.

## Persistence scope

The initial migration creates `repositories`, `analysis_jobs`, and `analysis_stages` with UUID identifiers, stable PostgreSQL enums, restrictive foreign keys, progress and non-empty-value checks, timezone-aware timestamps, and indexed relationship columns. Typed async repository classes flush but do not commit. Minimal application services own commit and rollback behavior and translate persistence failures into application errors.

SQLite is used only for portable unit coverage. PostgreSQL-specific enum and migration behavior is verified through offline SQL rendering; a live PostgreSQL integration suite remains future work.

## Internal ingestion security

Internal ingestion accepts only the previously normalized public GitHub HTTPS source. It invokes Git without a shell, uses clone depth 1, disables hooks and credential helpers, rejects local and extension protocols, avoids submodules, and captures bounded command output with a timeout. Repository code is never executed.

Each clone uses a unique validated directory beneath `DEVGUIDE_TEMPORARY_WORKSPACE_ROOT`. The directory is removed after success or failure. Post-clone scanning skips `.git`, dependency/build/cache directories, and symbolic links while enforcing configured repository bytes, file count, and individual file size. Successful ingestion records the commit, safely discovered default branch, and partial analysis progress; it does not complete the overall analysis.
