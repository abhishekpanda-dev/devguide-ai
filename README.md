# DevGuide AI

> Understand, improve, and ship unfamiliar codebases with confidence.

DevGuide AI is an evidence-first repository intelligence platform. The current implementation supports public repository submission, bounded ingestion and parsing, deterministic static code findings, repository structure and local dependency intelligence, evidence retrieval, single-question grounded answers, and a React frontend for the implemented public API. Broader reports remain planned.

## Project status

An early MVP foundation is implemented. It is not yet a complete working-application checkpoint: backend dependencies and a worker are required, and later analysis stages and reports remain unavailable.

## Planned workspace

- `apps/api` — API boundary (technology TODO)
- `apps/worker` — background analysis boundary (technology TODO)
- `apps/web` — React, TypeScript, and Vite frontend MVP
- `agents` — custom agent definitions (TODO)
- `skills` — custom skill definitions (TODO)
- `docs` — decisions, diagrams, and demo material
- `scripts` — repository automation (TODO)

See [PRD.md](PRD.md), [architecture.md](architecture.md), and [CONTRIBUTING.md](CONTRIBUTING.md) for the current foundation.

## Local development

See [apps/api/README.md](apps/api/README.md) for backend setup and [apps/web/README.md](apps/web/README.md) for frontend setup. A live end-to-end flow requires the API, PostgreSQL, Redis, and worker.

## License

MIT. See [LICENSE](LICENSE).
