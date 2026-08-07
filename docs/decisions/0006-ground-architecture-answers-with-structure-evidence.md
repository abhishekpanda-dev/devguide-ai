# ADR 0006: Ground architecture answers with persisted structure evidence

## Status

Accepted.

## Decision

Ask DevGuide deterministically detects architecture and dependency intent. For those questions only,
the server retrieves a bounded envelope of persisted language and directory summaries, probable entry
points, connectivity rankings, and local dependency edges. This trusted envelope is passed separately
from untrusted code excerpts to the configured `LLMProvider`.

Static edges describe resolved source relationships, not runtime execution. Entry points remain
heuristic candidates. Summary facts have no invented citation; an import-line claim may be cited only
when the normal persisted chunk retrieval and citation validator provide that source line.

## Consequences

Unrelated questions retain the existing lexical-only path. Mock mode remains deterministic and
offline. Claude receives bounded server-derived facts but cannot add evidence IDs or trusted
citations. Dynamic imports and unresolved modules are disclosed as limitations.

