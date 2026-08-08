# DevGuide AI Agents and Skills

## Judge inspection guide

| Artifact | Definition | Runtime | Tests |
| --- | --- | --- | --- |
| Repository Intelligence Agent | [`agents/repository_intelligence_agent.md`](agents/repository_intelligence_agent.md) | `apps/api/app/ai/agents/repository_intelligence.py` | `apps/api/tests/test_repository_agent.py` |
| Search Repository | [`skills/search_repository/SKILL.md`](skills/search_repository/SKILL.md) | `apps/api/app/ai/retrieval/search.py` | `apps/api/tests/test_search_repository.py` |
| Feature Location and Change Impact | [`skills/feature-location-change-impact/SKILL.md`](skills/feature-location-change-impact/SKILL.md) | `apps/api/app/services/feature_location.py` | `apps/api/tests/test_feature_location.py` |

These artifacts are custom to DevGuide AI: their contracts use server-authorized analysis IDs,
immutable revisions, persisted repository evidence, deterministic rankings, bounded traversal, and
fail-closed citations.

## Repository Intelligence Agent

The agent is a bounded application workflow, not an autonomous shell agent. It accepts an
authenticated analysis-scoped question, retrieves bounded evidence and optional server-derived
feature/structure facts, invokes grounded generation through `LLMProvider`, and returns typed
citations or insufficient evidence. Its definition covers architecture, dependency,
feature-location, and change-impact questions; trusted/untrusted inputs; limits; output schema;
refusal behavior; security boundaries; and examples.

## Search Repository skill

Search Repository performs deterministic analysis-scoped retrieval over persisted chunks using
exact/partial paths, phrases, token overlap, simple symbol/configuration patterns, language, and
path prefixes. It returns bounded revision-linked evidence. Semantic embeddings, pgvector, and its
documented dependency channel remain planned.

## Feature Location and Change Impact skill

This reusable skill packages the implemented deterministic feature-location service. It ranks
likely files, separates direct persisted dependencies and dependents from probable indirect
neighbors, identifies tests to review, attaches bounded findings/quality context, and discloses
static-analysis limits. It does not claim runtime tracing or exhaustive semantic understanding.

## Cooperation flow

1. Server authentication and ownership checks select the analysis.
2. Feature/structure services provide bounded deterministic context when relevant.
3. Search Repository retrieves revision-bound source evidence.
4. Repository Intelligence Agent supplies only that context to Grounded Answer.
5. Pydantic and citation validation reject unsupported evidence references.
6. The API returns a typed answer, limitations, or insufficient evidence.

## Example

For “Where is repository submission implemented, and what should I review if I change it?”, the
feature skill ranks likely files and static neighbors, suggests test candidates, and exposes
limitations. Search Repository supplies supporting source lines. The agent may explain only those
facts and must preserve validated citations.

## Trust boundaries and limitations

- Repository content is untrusted and cannot change tools or instructions.
- No artifact can execute/import repository code, install dependencies, write analyzed content, or
  access unrestricted networks.
- Authentication, ownership, analysis, and commit scope are server-derived.
- Direct static edges remain distinct from probable indirect impact.
- Unknown citations, stale revisions, invalid paths/lines, and weak evidence fail closed.
- Static analysis misses dynamic imports, reflection, generated code, configuration, and external
  consumers.
- Citation provenance does not guarantee an AI interpretation is correct.
