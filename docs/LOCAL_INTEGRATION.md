# Local end-to-end integration

This guide runs the implemented DevGuide AI path: submit a supported public GitHub repository,
process it in the worker, inspect persisted dashboard results, ask an evidence-grounded question,
and generate a suggested fix for a persisted finding. It does not enable planned features or run
code from an analyzed repository.

## Prerequisites and configuration

- Python 3.11+, Node.js 20+, npm, Docker, and Git.
- Copy the safe variable names from `.env.example` into a local `.env`; never commit secrets.
- The Docker defaults expose PostgreSQL on `5433` and Redis on `6380`.
- Set `VITE_DEVGUIDE_API_URL=http://127.0.0.1:8000` for the frontend. The value is read when
  Vite starts, so restart Vite after changing it.
- Mock AI is the deterministic offline default. For Claude, set
  `DEVGUIDE_AI_PROVIDER=claude`, `DEVGUIDE_ANTHROPIC_API_KEY`, and the optional bounded Claude
  settings documented in `apps/api/README.md`, then restart the API. Never put the key in logs.

## Start order

Run each long-lived process in its own terminal.

1. Start dependencies from the repository root: `docker compose up -d postgres redis`.
2. From `apps/api`, create/activate `.venv`, install `.[dev]`, and run `alembic upgrade head`.
3. From `apps/api`, start the API: `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
4. From `apps/api`, start exactly one worker: `arq app.worker.WorkerSettings`.
5. From `apps/web`, install dependencies and start the frontend: `npm install`, then
   `npm run dev -- --host 127.0.0.1 --port 5173`.

Check `/api/v1/health` and `/api/v1/ready` before submitting. If `5173` is already owned by
another application, use `5174`; both origins are included in the local CORS defaults. Do not stop
an unrelated process merely to reclaim a preferred port.

## Manual integration checklist

1. Open the frontend and submit a supported public GitHub HTTPS repository.
2. Confirm the progress page advances from queued/running to completed or an explicit partial
   state. Refresh once and confirm the persisted state remains.
3. Open the repository dashboard. Verify repository identity, analyzed revision, file/language
   totals, findings, structure, quality, and empty states against API responses.
4. In the dependency view, search for a persisted file, switch Bundle / Flow / Tree, apply filters,
   select the file, and verify dependencies, dependents, and exact revision source links.
5. Ask one general, architecture/dependency, and feature-location question. Confirm evidence,
   limitations, provider/model metadata, and exact source links are visible.
6. From a feature-location answer, use **Focus in graph** and **Ask about this file**. Confirm the
   persisted path is selected or prefilled; query-string text must never create graph data.
7. If the analysis has a persisted finding, request a suggested fix. Confirm it is clearly
   advisory, cited, and does not modify repository files.
8. Open Planned Tools. Confirm its explicit non-operational notice and that choosing a card makes
   no API request.
9. Repeat the dashboard check at desktop and mobile widths. Mobile should default to Tree.

## Failure and recovery checks

- **API unavailable:** the frontend should show a safe connection error. Correct
  `VITE_DEVGUIDE_API_URL` and restart Vite.
- **Worker unavailable:** a submission remains queued. Start one worker; the persisted job should
  be claimed and complete without resubmission.
- **Redis unavailable:** submission returns a safe dispatch failure with a correlation ID. Restore
  Redis and restart the worker if it exited; ARQ does not automatically recover in every local
  outage sequence.
- **PostgreSQL unavailable:** readiness fails. Restore PostgreSQL before accepting work.
- **Claude key missing:** Claude mode returns `ai_provider_not_configured` without exposing secrets.
  Restore mock mode or configure a valid local key and restart the API.
- **Port conflict or stale process:** identify the exact owning process, verify its command line,
  and stop only a DevGuide process you started. A root ARQ launcher may have Python child
  processes; count that as one worker process tree, not several workers.

Errors exposed by the UI/API should contain a stable safe message and correlation ID, never a
stack trace, credential, temporary clone path, or unrestricted filesystem detail.

## Validation

From `apps/api`, run `ruff format --check .`, `ruff check .`, `mypy app tests`, and `pytest`.
From `apps/web`, run `npm run format:check`, `npm run lint`, `npm run typecheck`,
`npm run test -- --run`, and `npm run build`. From the repository root, run
`git diff --check` and inspect `git status --short` to ensure generated output, local `.env` files,
logs, dependencies, and secrets are not tracked.
