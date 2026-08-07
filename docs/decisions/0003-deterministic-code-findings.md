# ADR 0003: Persist bounded deterministic code findings

## Status

Accepted

## Decision

Run a bounded deterministic findings pass after parser persistence and before analysis completion. Scan only accepted in-memory parser output, never execute repository code, and persist findings plus a per-analysis readiness marker. Keep findings isolated by analysis job and derive source links at the API boundary from trusted normalized GitHub metadata and the analyzed commit.

Rules produce review leads in fixed severity and category enums. Evidence is bounded, credential-like values are redacted, and a configured maximum limits stored results. A zero-finding result is represented by metadata so it differs from an analysis that is not ready.

## Consequences

Duplicate worker delivery can be handled idempotently, filters remain database-scoped, and exact links cannot be controlled by repository text. The rule set is intentionally narrow and cannot replace a full language-aware security analyzer. Findings-stage failure marks the analysis failed but does not remove parser data already committed.
