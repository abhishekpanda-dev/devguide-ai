# DevGuide AI API

This directory contains the FastAPI foundation, a minimal ARQ analysis worker, parser
persistence, and the internal runtime Search Repository skill foundation. Repository submission
commits its records and dispatches the analysis ID to Redis. The worker safely claims queued work
and persists analysis-scoped parser output.

The internal ingestion service now supplies secure cloning primitives for an existing repository and analysis job. It is not exposed through a public endpoint and no background worker invokes it yet.

## Internal Search Repository skill

`SearchRepositorySkill.search` accepts a typed analysis ID, natural-language query, optional
language filters and repository-relative path prefix, result limit, and minimum score. It applies
scope and filters in the repository layer, then deterministically ranks exact/partial paths,
phrases, token overlap, simple symbol-like declarations and configuration keys, and filter
matches. Identical and overlapping chunks are removed.

Every citation is revalidated for repository-relative POSIX path, one-based inclusive bounds,
chunk hash, and commit SHA. Invalid evidence fails closed. There is no standalone public search
endpoint. Semantic embeddings and pgvector are not implemented;
search requires no network or AI provider.

## Internal grounded-answer generation

The API package now includes a typed asynchronous `LLMProvider`, a Claude implementation, and a
deterministic `MockLLMProvider`. `GroundedAnswerService` converts validated Search Repository
evidence into bounded, explicitly untrusted prompt data, validates structured provider output,
and derives citations only from supplied evidence IDs. Invalid or fabricated citations fail
closed; duplicates are removed. Empty search evidence returns insufficient evidence without a
provider call.

Claude requests have configured time, output-token, evidence-count, evidence-character, retry,
and temperature bounds. Only transient failures and timeouts are retried. Provider details are
translated to stable application errors. Automated tests inject mock clients and never call the
network. The public boundary is limited to the single repository-question endpoint; chat history
and embeddings are not implemented.

## Internal Repository Intelligence Agent

`RepositoryIntelligenceAgent.run` now provides the internal bounded question-answering workflow.
It validates a typed analysis-scoped request, forwards lexical retrieval filters to Search
Repository, verifies the returned analysis scope, rejects malformed evidence, removes exact
duplicates, applies deterministic ordering and limits, and calls Grounded Answer only when useful
evidence remains. Final citations are checked against the retrieved chunk, path, line range, hash,
and repository-file ID before return.

Dependencies are injected, and an internal factory wires Search Repository and Grounded Answer to
either the configured Claude provider or an injected provider. Agent tests use
`MockLLMProvider` with typed fakes and require no PostgreSQL, Redis, GitHub, network, or API key.
Only the minimal repository-question endpoint described below is public; semantic embeddings
remain unimplemented.

## Repository-question endpoint

`POST /api/v1/analyses/{analysis_id}/questions` is the minimal public boundary over the runtime
agent. Only `question` is required. Optional language, path-prefix, retrieval-limit,
minimum-score, and citation-limit controls are validated and mapped into the internal agent
request; the analysis ID always comes from the path. Responses contain evidence-backed citations
and preserve the request correlation ID.

The API accepts questions only for existing running or completed analyses that already have
persisted chunks. Insufficient evidence returns `200` without calling the provider. Provider,
search, grounded-answer, and agent dependencies are constructed outside the handler and can be
overridden in tests. The deterministic offline mock is the local/test default. Automated tests use
the mock provider and make no network calls.

This endpoint has no chat history, authentication, streaming, SSE, WebSockets, embeddings, or
frontend integration.

### Local Claude answers

To opt into live Claude answers locally, set these variables in the repository `.env` and restart
the API:

```dotenv
DEVGUIDE_AI_PROVIDER=claude
DEVGUIDE_ANTHROPIC_API_KEY=your-local-secret
DEVGUIDE_CLAUDE_MODEL=claude-sonnet-4-5
DEVGUIDE_AI_REQUEST_TIMEOUT_SECONDS=30
DEVGUIDE_AI_MAXIMUM_OUTPUT_TOKENS=1024
DEVGUIDE_AI_TEMPERATURE=0
DEVGUIDE_AI_RETRY_COUNT=2
```

Do not commit the key. A missing or blank key returns `ai_provider_not_configured`. Provider
timeouts and failures are translated to safe application errors, and raw Anthropic error details
are not returned. Repository excerpts remain bounded untrusted prompt data; response citations
are reconstructed from retrieved database evidence rather than accepted from Claude.

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

For local frontend development, `DEVGUIDE_CORS_ALLOWED_ORIGINS` accepts a JSON array of explicit
HTTP(S) origins. Its safe defaults cover Vite on ports 5173 and 5174 through both `localhost` and
`127.0.0.1`. Wildcard origins are rejected; deployments should replace the defaults with their
exact trusted frontend origins.

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
