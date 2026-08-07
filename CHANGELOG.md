# Changelog

All notable changes will be documented here. The project intends to follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and semantic versioning once releases begin.

## [Unreleased]

### Added

- Initial repository structure and foundational documentation placeholders.
- FastAPI database and persistence foundation for repositories, analysis jobs, and analysis stages, including typed async repositories, service transaction boundaries, and the first Alembic migration.
- Public-GitHub repository submission and repository/analysis status API foundation with strict offline URL normalization and bounded uniqueness-race recovery.
- Internal secure public-GitHub ingestion primitives with shallow clone command restrictions, bounded temporary workspaces, repository limit scanning, metadata persistence, and guaranteed cleanup.
- ARQ-backed typed analysis dispatch and a separately runnable minimal worker.
- Atomic queued-job claiming and idempotent `repository_ingestion` stage orchestration with safe dispatch and stage failure persistence.
- Internal deterministic repository parser foundation with extension-based language detection, safe file filtering, typed metadata, line chunking, and repository statistics.
- Analysis-scoped parser persistence and worker integration across ingestion, parsing, durable provenance, and guaranteed workspace cleanup.
- Internal runtime Search Repository skill foundation with typed analysis-scoped queries,
  deterministic lexical/path/symbol-like ranking, filters, duplicate and overlap removal,
  validated citations, and explicit insufficient-evidence results. Semantic embeddings remain
  unimplemented.
- Internal typed `LLMProvider`, asynchronous Claude provider, deterministic mock provider,
  injection-resistant bounded prompts, structured grounded-answer validation, evidence-derived
  citations, safe provider errors, and bounded transient retries. No public chat endpoint or full
  Repository Intelligence Agent orchestration is included.
- Bounded runtime Repository Intelligence Agent foundation combining analysis-scoped deterministic
  Search Repository retrieval with Grounded Answer generation, independent evidence and citation
  validation, deterministic deduplication and ordering, insufficient-evidence short-circuiting,
  dependency injection, safe agent errors, and external-service-free tests.
- Minimal `POST /api/v1/analyses/{analysis_id}/questions` endpoint with typed request/response
  validation, analysis readiness checks, correlation propagation, dependency-injected provider and
  agent wiring, stable question errors, and offline mock-provider API tests.
- React and TypeScript frontend MVP with repository submission, polled analysis progress,
  repository metadata, bounded evidence-backed questions, accessible responsive styling, typed API
  errors, and mocked interaction tests.

TODO: Define the first release milestone and versioning policy.
