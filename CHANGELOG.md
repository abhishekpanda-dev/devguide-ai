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
  validated citations, and explicit insufficient-evidence results. Semantic embeddings, Claude,
  and answer generation remain unimplemented.

TODO: Define the first release milestone and versioning policy.
