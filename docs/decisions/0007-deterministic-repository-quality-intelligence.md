# ADR 0007: Persist deterministic repository quality intelligence

## Status

Accepted.

## Decision

The worker runs `repository_quality` after repository intelligence and before ready. It analyzes the
already parsed in-memory source records without executing or importing repository code. Version
`quality-v1` reports conservative Python top-level unused-code candidates, exact normalized Python
top-level duplicate blocks, and a deterministic four-category score.

Duplicate blocks are bucketed by SHA-256 fingerprint after safely removing Python comments and layout
tokens. Minimum line/token thresholds and group/member caps prevent trivial or unbounded results.
Unused candidates require a unique persisted lexical occurrence and exclude tests, generated/vendor/build
content, probable entry points, and common framework/magic names.

Each category begins at 100. Capped deductions are high findings: 8 each/32 maximum (security), warning
findings: 3 each/24 maximum (reliability), info findings: 1 each/12 maximum (maintainability), duplicates:
2 each/15 maximum, unused candidates: 1 each/10 maximum, and files with at least ten resolved outbound
edges: 4 each/20 maximum (structure). Overall score is the rounded mean of category scores.

## Consequences

The score is reproducible and Claude-independent, but it is neither a benchmark nor proof of quality.
Dynamic references, unsupported languages, semantic clones, and runtime behavior may cause false positives
or false negatives and are disclosed as limitations.

