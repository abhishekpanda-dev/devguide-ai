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

TODO: Define the first release milestone and versioning policy.
