# DevGuide AI API

This directory contains the implemented FastAPI foundation only. It provides versioned liveness and database-backed readiness endpoints, environment settings, async SQLAlchemy session infrastructure, Alembic configuration, JSON logging, correlation IDs, centralized errors, and unit tests. Repository analysis and AI functionality are not implemented.

## Requirements

- Python 3.11+
- PostgreSQL for a successful readiness check (tests do not require it)

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
python -c "from app.main import app; assert app.title == 'DevGuide AI API'"
```

Configuration uses `DEVGUIDE_`-prefixed environment variables. See the repository `.env.example`. Never place production credentials in that file or logs.

## Endpoints

- `GET /api/v1/health` reports process liveness without contacting external services.
- `GET /api/v1/ready` verifies required dependencies through `ReadinessService`; the default implementation performs a PostgreSQL `SELECT 1` and returns `503` on failure.

All responses include `X-Correlation-ID`. A valid UUID supplied in that header is preserved; other values are replaced. Error responses use the documented centralized envelope.
