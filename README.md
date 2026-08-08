# DevGuide AI
<img width="944" height="488" alt="Screenshot 2026-08-08 121911" src="https://github.com/user-attachments/assets/20744428-b852-41b1-b323-b29c8bf5fb93" />
<img width="943" height="491" alt="image" src="https://github.com/user-attachments/assets/eb70d7d9-399d-4e0f-a46d-794d6fbb9fc0" />
<img width="961" height="550" alt="WhatsApp Image 2026-08-08 at 4 38 17 PM" src="https://github.com/user-attachments/assets/9541f102-621d-4488-a05c-56a4a1462372" />



> Understand, improve, and ship unfamiliar codebases with confidence.

DevGuide AI is an evidence-first repository intelligence platform. The implemented MVP supports
local authentication, public repository submission, bounded ingestion and parsing, deterministic
findings, structure/dependency intelligence, quality scoring, grounded repository questions, and a
React frontend.

## Project status

An early end-to-end MVP is implemented. PostgreSQL, Redis, the FastAPI API, ARQ worker, and web
application must run for the live flow. Semantic/vector retrieval, broader reports, private
repositories, and production hardening remain planned.

## Workspace

- `apps/api` - FastAPI API, shared services, ARQ worker, and Alembic migrations
- `apps/worker` - worker deployment boundary
- `apps/web` - React, TypeScript, and Vite frontend
- `agents` - custom agent definitions
- `skills` - reusable custom skill artifacts
- `docs` - decisions, diagrams, demo, and integration guidance

See [PRD.md](PRD.md), [architecture.md](architecture.md), and
[CONTRIBUTING.md](CONTRIBUTING.md).

## Local development

Follow [apps/api/README.md](apps/api/README.md) and [apps/web/README.md](apps/web/README.md). The
live flow requires PostgreSQL, Redis, API, worker, and frontend.

## Hackathon Entry Checkpoints

- [Architecture](architecture.md)
- [Coding-agent rules](AGENTS.md)
- [Custom agents and skills](AGENTS_AND_SKILLS.md)
- [Repository Intelligence Agent](agents/repository_intelligence_agent.md)
- [Search Repository skill](skills/search_repository/SKILL.md)
- [Feature Location and Change Impact skill](skills/feature-location-change-impact/SKILL.md)
- [GitHub Actions workflow](.github/workflows/bootstrap.yml)
- [Live demo checklist](docs/demo/README.md)

Backend validation from `apps/api`:

```text
python -m ruff format --check .
python -m ruff check .
python -m mypy app tests
python -m pytest
```

Frontend validation from `apps/web`:

```text
npm run format:check
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

The workflow defines required CI checks. Its presence does not prove a green remote run.

## License

MIT. See [LICENSE](LICENSE).
