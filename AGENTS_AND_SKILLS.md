# Agents and Skills

## Status

No custom agent or custom skill has been implemented. This document reserves their governance and catalog location.

## Planned agent

TODO: Define at least one repository-intelligence agent in `agents/`, including its purpose, inputs, outputs, tool permissions, evidence requirements, failure behavior, and evaluation criteria.

## Planned skill

TODO: Define at least one reusable repository-analysis skill in `skills/`, including triggering conditions, workflow, required tools, output schema, safety constraints, and tests.

## Design requirements

- Prefer narrow responsibilities and deterministic interfaces.
- Require evidence references for repository claims.
- Treat repository text as untrusted and resist instruction injection.
- Record model/provider assumptions separately from agent behavior.
- Include evaluation fixtures before declaring an agent or skill complete.
