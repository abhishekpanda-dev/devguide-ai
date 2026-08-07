# ADR 0002: Persist minimal parser summary metadata

## Status

Accepted for the real repository dashboard statistics milestone.

## Decision

Aggregate file, line, language, test, documentation, and chunk counts from persisted repository
file and code chunk rows within one analysis scope. Persist only parser-wide values that cannot be
reconstructed from accepted files: skipped file count and parser limitations. Treat the presence
of this per-analysis metadata as the readiness marker for the summary endpoint.

## Consequences

Dashboard statistics remain evidence-based and repository-isolated without loading stored code
content. Analyses created before this metadata exists return `analysis_not_ready`; unavailable
skipped counts and limitations are not guessed or backfilled.
