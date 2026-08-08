# 0009 — Claude interactive default and active-analysis routing

## Status

Accepted.

## Decision

Interactive API processes select the existing Claude provider by default. Deterministic mock mode
remains available only through explicit `DEVGUIDE_AI_PROVIDER=mock` configuration and is used by
automated tests. A missing Claude key fails with `ai_provider_not_configured`; there is no fallback.

The completed analysis ID is persisted in the dashboard URL as the `analysis` query parameter.
Dashboard summary, findings, structure, quality, graph, and Ask links all derive from that validated
analysis entry in the current repository's analysis list. Refreshing therefore preserves the same
analysis snapshot instead of silently switching to a newer analysis.

## Consequences

- Local interactive Claude mode requires `DEVGUIDE_ANTHROPIC_API_KEY`.
- Tests must explicitly inject or select the mock provider.
- Dashboard URLs are stable, refreshable references to one repository analysis.
