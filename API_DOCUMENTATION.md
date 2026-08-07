# API Documentation

## Status

The FastAPI, persistence, repository submission, minimal asynchronous ingestion worker, parser
persistence, and internal deterministic Search Repository foundation are implemented under
`apps/api`. Submission commits database records, then enqueues the analysis ID through a typed
ARQ queue adapter. It never clones during the API request. Reports, chat, semantic indexing, and
AI functionality remain unimplemented.

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

An existing normalized repository is reused, while every accepted submission creates a new queued analysis job using the configured pipeline version. After commit, the analysis ID is dispatched to Redis. Dispatch failure preserves the record, marks it failed with `analysis_dispatch_failed`, and returns a safe `503` error. This endpoint never clones repository content.

## Worker lifecycle

The ARQ worker atomically claims queued jobs and orchestrates `repository_ingestion` followed by `repository_parsing`. It retains one temporary workspace across both stages and removes it after success or failure. Successful parsing persists the analysis-scoped snapshot, completes the parsing stage, and leaves the analysis running at 40%. Duplicate completed deliveries are no-ops. Redis is required for real dispatch and execution, not unit tests.

## Internal repository parser

The internal `RepositoryParser` converts an existing workspace into typed file records, deterministic line chunks, and summary statistics. Language detection is extension-based for Python, JavaScript, TypeScript, Java, HTML, CSS, JSON, YAML, Markdown, and TOML. Binary, unsupported, oversized, media, archive, executable, symbolic-link, and ignored-directory content is skipped.

The parser has no public endpoint. Its output is transactionally stored in `repository_files` and `code_chunks`, preserving repository ID, analysis ID, commit SHA, relative path, hashes, parser version, and one-based inclusive ranges. Replacement for the same analysis is idempotent. It does not perform AST extraction, framework detection, AI inference, embeddings, network access, or repository-code execution.

## Internal Search Repository skill

There is no standalone public search endpoint. Internal callers use a typed request containing
`analysis_job_id`, `query`, optional `languages`, optional repository-relative `path_prefix`,
`limit`, and `minimum_score`. Results contain persisted evidence provenance, deterministic scores,
matched channels, counts, coverage, and limitations.

Analysis, language, and prefix constraints are applied before candidate return. Ranking uses
bounded constants for exact/partial paths, exact phrases, token overlap, simple symbol-like
matches, language, and prefix signals. Ordering and identical/overlap removal are deterministic.
Citation validation fails closed on invalid paths, bounds, hashes, or commit provenance. No
embeddings, pgvector, Claude, network access, learned reranking, or final answer generation are
involved.

## Internal grounded-answer generation

The internal `GroundedAnswerService` accepts a question and a
Search Repository result, bounds validated lexical evidence by configured item and character
limits, and calls the typed asynchronous `LLMProvider`. Provider output is structured and contains
answer text, cited chunk IDs, evidence quality, insufficient-evidence state, limitations, and safe
usage/finish metadata when available.

The Claude provider uses asynchronous requests, configured timeouts and output limits, and retries
only timeouts or transient HTTP statuses. Missing configuration, unavailable providers, timeouts,
malformed responses, and grounding failures map to stable application errors without exposing raw
provider exceptions. Repository content is delimited as untrusted data and never enters system
instructions. Citations are reconstructed from the supplied evidence, so paths, ranges, and hashes
cannot be supplied or altered by the model. Automated tests use `MockLLMProvider` or a mocked
Claude client; no real API request is made. Embeddings, pgvector, and agent orchestration remain
unimplemented.

## Internal Repository Intelligence Agent

The internal typed agent accepts an analysis ID, question, optional
language and path-prefix filters, retrieval score/limit controls, citation limit, and correlation
ID. It invokes deterministic lexical Search Repository retrieval, independently verifies analysis
scope and citation metadata, removes duplicate evidence, orders it deterministically, and invokes
Grounded Answer through dependency injection.

An empty or below-threshold retrieval returns a typed insufficient-evidence response without any
provider call. Successful results contain only validated evidence-derived citations plus safe
provider/model metadata and limitations. Search and answer failures are translated into stable
agent errors without exposing database or provider details. Runtime tests use `MockLLMProvider`
and typed fakes; no external service is required. Public chat, embeddings, streaming,
authentication, and full product orchestration remain unimplemented.

## `POST /api/v1/analyses/{analysis_id}/questions`

Exposes the bounded Repository Intelligence Agent for one question about one persisted analysis.
The analysis ID comes only from the path. The body requires `question` and optionally accepts
`language_filters`, `path_prefix`, `retrieval_limit`, `retrieval_minimum_score`, and
`maximum_citations`.

The endpoint returns `200` with the typed agent response: answer, evidence quality,
insufficient-evidence state, retrieved count, safe provider/model metadata, limitations,
correlation ID, and validated citations containing chunk and repository-file IDs, relative path,
one-based inclusive lines, and content hash. Insufficient evidence is also a successful `200`
response with no citations or provider call.

Before agent execution, the API requires an existing running or completed analysis with persisted
chunks. Missing analyses return `analysis_not_found`; other states or missing chunks return
`analysis_not_ready`. Invalid bodies return `repository_question_invalid`, and safely translated
agent failures return `repository_question_failed`.

`DEVGUIDE_AI_PROVIDER=mock` is allowed for local/test environments. `claude` mode requires
`DEVGUIDE_ANTHROPIC_API_KEY`. The route performs no provider construction. There is no chat
history, authentication, streaming, SSE, WebSocket behavior, or semantic embedding retrieval;
answers use deterministic lexical evidence and validated citations.

The runtime default is `mock`. Local live generation is enabled with
`DEVGUIDE_AI_PROVIDER=claude` plus `DEVGUIDE_ANTHROPIC_API_KEY`. The model, request timeout,
maximum output tokens, temperature, and bounded transient retry count use
`DEVGUIDE_CLAUDE_MODEL`, `DEVGUIDE_AI_REQUEST_TIMEOUT_SECONDS`,
`DEVGUIDE_AI_MAXIMUM_OUTPUT_TOKENS`, `DEVGUIDE_AI_TEMPERATURE`, and
`DEVGUIDE_AI_RETRY_COUNT`. A missing key returns `ai_provider_not_configured`; provider details
and keys are never included in the public error envelope.

## `GET /api/v1/analyses/{analysis_id}/findings`

Returns persisted deterministic findings for exactly one analysis. Optional query parameters are `severity` (`info`, `warning`, or `high`), `category` (`maintainability`, `reliability`, or `security`), `path_prefix` (validated repository-relative path), and `limit` (1–500). The response includes matching items, total matching count, whole-analysis severity counts, and parser/analyzer limitations.

Each item contains a stable rule ID, severity, category, title, repository-relative path, one-based inclusive line range, bounded evidence excerpt, explanation, suggested action, confidence, and an exact GitHub blob link pinned to the analyzed commit. Links are derived from trusted stored repository metadata; repository content cannot supply their host or commit.

The current deterministic rules cover TODO/FIXME/HACK markers, large application source files, and selected Python constructs: `eval`, `exec`, broad/empty exception handlers, `subprocess` with shell mode, likely hardcoded credentials, debug enablement, and HTTP requests without explicit timeouts. Dependency lockfiles, generated/minified artifacts, source maps, and files under common dependency or build-output directories are excluded only from the large-file rule. These findings are bounded review leads and do not constitute a complete security analysis. No repository code is executed and no AI provider is called. A missing analysis returns `analysis_not_found` (404); missing findings data returns `analysis_not_ready` (409).

## `GET /api/v1/repositories/{repository_id}`

Returns a repository record or `repository_not_found` with `404`.

## `GET /api/v1/analyses/{analysis_id}`

Returns an analysis-job status record or `analysis_not_found` with `404`.

## `GET /api/v1/repositories/{repository_id}/analyses`

Returns `{items, limit, offset}` for the repository. `limit` is between 1 and 100; `offset` is non-negative.

## Unresolved contract work

Authentication, rate limits, idempotency beyond repository reuse, retention, worker dispatch, and full asynchronous lifecycle semantics remain undecided.
# AI suggested fixes

`POST /api/v1/analyses/{analysis_id}/findings/{finding_id}/suggested-fix` generates an optional,
advisory probable fix for an existing deterministic finding. The request has no body: all source
evidence, paths, lines, hashes, and commit metadata are loaded from trusted persisted analysis data.
Context is bounded by `DEVGUIDE_AI_MAXIMUM_EVIDENCE_CHARACTERS`, credential-like values are
redacted, and citations are validated and reconstructed by the API. Repository files are never
modified. Use mock mode for deterministic offline testing; configured Claude requests may incur
provider costs. Always review a suggestion before applying it.

The findings API remains backward compatible. Its deterministic analyzer centrally excludes
supported lockfiles, generated/build/vendor content, minified assets, and source maps. New stable
rule IDs are `python.mutable-default-argument`, `python.bare-except`, `python.runtime-assert`, and
`security.tls-verification-disabled`. Exact commit, path, and line citations are unchanged.

## Repository structure

`GET /api/v1/analyses/{analysis_id}/structure` returns persisted files, probable entry points,
repository-local dependency edges, coupling counts, language/directory summaries, limitations, and
trusted immutable GitHub evidence links. Optional `language`, repository-relative `path_prefix`,
`relationship_type` (`imports`, `requires`, or `reexports`), and bounded `limit` filters are
supported. Client input cannot create edges or source metadata. Zero-edge completed analyses return
an empty edge list rather than a not-ready error.
# Architecture-aware questions

`POST /api/v1/analyses/{analysis_id}/questions` remains the single question endpoint. Questions about
architecture, entry points, modules, dependencies, usage, data flow, service layers, connectivity, or
coupling additionally use bounded persisted structure evidence. The response adds the backward-compatible
`structure_evidence_used` boolean.

Dependency relationships are static source relationships and do not prove runtime behavior. Entry points
are probable heuristic candidates. Structure summaries are returned to the answer model as trusted facts
but do not acquire fabricated source citations; normal citations continue to be accepted only from
validated persisted chunks. Mock mode is deterministic and offline, while configured Claude mode consumes
the same bounded code and structure envelope.
