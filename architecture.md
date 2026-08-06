# Architecture

## Status

Proposed boundaries only; no application architecture has been implemented.

## Planned components

1. **Web application (`apps/web`)** — repository submission and analysis presentation.
2. **API (`apps/api`)** — request validation, orchestration, and result access.
3. **Worker (`apps/worker`)** — asynchronous repository ingestion and analysis.
4. **Agents (`agents`)** — repository-intelligence agent definitions.
5. **Skills (`skills`)** — reusable, scoped analysis workflows.

## Conceptual flow

Public repository reference → API → queued analysis → worker/agent/skills → evidence-backed results → API → web application.

## Architectural principles

- Preserve traceability from generated claims to repository evidence.
- Treat repository content as untrusted input.
- Keep provider-specific AI integration behind a boundary.
- Separate interactive requests from long-running analysis.
- Minimize collected data and define retention explicitly.

## Unresolved decisions

TODO: Record accepted choices in `docs/decisions`, including runtime technologies, storage, queueing, authentication, authorization, observability, rate limiting, deployment, and failure recovery.
