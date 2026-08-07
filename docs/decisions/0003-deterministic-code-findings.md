# ADR 0003: Persist bounded deterministic code findings

## Status

Accepted

## Decision

Run a bounded deterministic findings pass after parser persistence and before analysis completion. Scan only accepted in-memory parser output, never execute repository code, and persist findings plus a per-analysis readiness marker. Keep findings isolated by analysis job and derive source links at the API boundary from trusted normalized GitHub metadata and the analyzed commit.

Rules produce review leads in fixed severity and category enums. Evidence is bounded, credential-like values are redacted, and a configured maximum limits stored results. A zero-finding result is represented by metadata so it differs from an analysis that is not ready.

## Consequences

Duplicate worker delivery can be handled idempotently, filters remain database-scoped, and exact links cannot be controlled by repository text. The rule set is intentionally narrow and cannot replace a full language-aware security analyzer. Findings-stage failure marks the analysis failed but does not remove parser data already committed.

## File classification and applicability

One repository-relative, traversal-safe policy classifies source, test, configuration,
documentation, dependency metadata, lockfiles, generated content, build output, vendor content,
minified files, and unknown text. Lockfiles, generated/build/vendor content, minified assets, and
source maps are excluded from findings. Large-file applies only to source. TODO/FIXME/HACK apply to
source, test, configuration, documentation, and unknown accepted text. Credential matching applies
only to source and configuration. Python AST rules apply to Python source and tests, except runtime
assert, which excludes tests.

Info is a low-priority lead, warning deserves focused review, and high identifies a strong
security-impact signal. Confidence is a stable deterministic property of each rule. Findings can
still contain false positives or miss behavior and remain review signals, not confirmed issues.
