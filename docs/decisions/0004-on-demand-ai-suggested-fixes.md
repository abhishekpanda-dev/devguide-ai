# 0004: Generate AI suggested fixes on demand without persistence

## Decision

AI suggested fixes are generated only after an explicit user request. The API loads the finding,
file, bounded persisted chunks, commit metadata, and citation data within one analysis scope. It
redacts suspected credentials before invoking the configured provider and reconstructs citations
from trusted persistence. Suggestions are not stored and never modify repository files.

## Consequences

Deterministic findings remain the source of truth. Suggestions can become unavailable when the
provider is unavailable and may differ between live requests. They are advisory, may be incorrect,
and must be reviewed before applying. Mock mode is deterministic and network-free; Claude mode
requires configuration and may incur provider costs.
