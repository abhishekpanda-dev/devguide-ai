# DevGuide AI live demo checklist

This is a reproducible checklist, not evidence that a run passed. Record the environment,
repository, commit, tester, and result when it is performed.

## Preconditions

- PostgreSQL is at Alembic head.
- Redis, FastAPI, the ARQ worker, and the Vite frontend are running and ready.
- Mock mode is explicitly selected for an offline demo, or Claude is explicitly configured.
- Use a supported public repository within configured bounds.

## Flow

1. Register or sign in.
2. Submit a public repository URL.
3. Observe analysis progress through queued and processing states.
4. Wait for `ready` and 100%, recording any partial-stage limitations.
5. Open the dashboard and confirm repository identity and analyzed commit.
6. Inspect Findings and evidence, or its explicit empty state.
7. Inspect Quality scores, deductions, candidates, and limitations.
8. Inspect Structure languages, entry points, coupling, and dependencies.
9. Exercise Bundle, Flow, and Tree views, including keyboard controls.
10. Ask DevGuide an answerable question and verify each citation resolves to the analyzed commit.
11. Ask an unsupported question and verify an insufficient-evidence response.
12. Log out and confirm protected routes no longer expose the workspace.

Mark the live flow PASS only after every step is observed. Store screenshots or recordings outside
the repository unless explicitly approved.
