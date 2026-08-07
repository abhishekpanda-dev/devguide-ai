# DevGuide AI web

React frontend MVP for the existing DevGuide AI API. It displays only data returned by documented
public endpoints, including repository summaries, findings, structure, quality scores, and grounded
questions. Chat history and streaming are not available.

## Dashboard and dependency visualization

The repository overview is a compact dark intelligence workspace with a repository toolbar,
analysis-summary sidebar, evidence-focused center workspace, and findings/quality/actions panel.
Every metric comes from the existing repository, summary, findings, structure, and quality APIs.
Optional panel failures remain local and use the existing safe correlation-ID errors.

Dashboard Phase 2 uses a custom SVG radial Bundle built with `d3-hierarchy` and `d3-shape` as the
desktop default, retains `@xyflow/react` as the Flow view, and provides a native accessible Tree
view. All three modes are derived exclusively from the persisted structure response. File nodes are
colored by language by default (with optional top-folder coloring), sized by bounded dependency
count, and marked when the server identifies a probable entry point. Directed edge treatments
distinguish imports, requires, and reexports.

Rendering is deterministically bounded to 80 nodes and 160 resolved edges, with a visible notice
when data is omitted. Isolated files are hidden by default and can be explicitly restored.
Unresolved targets are ignored. Filters and search operate on an immutable client-side projection
and do not create analysis facts. Exact source links are displayed only when the structure API
supplies them. Bundle and Flow are replaced by the simpler Tree view on mobile.

The visualization represents supported static local relationships, not runtime behavior or a
complete dependency graph. Matrix, Treemap, and Cluster modes remain deferred.

## Local development

Requirements: Node.js 20+ and npm.

```bash
npm install
npm run dev
```

Set `VITE_DEVGUIDE_API_URL` to the API origin (for example `http://localhost:8000`). Leave it empty when the frontend and `/api/v1` API share an origin. The FastAPI backend, PostgreSQL, Redis, and worker must be configured separately for a live end-to-end flow.

## Routes

- `/` — submit a public GitHub repository.
- `/analyses/:analysisId` — observe queued or running analysis and terminal status.
- `/repositories/:repositoryId` — view repository metadata and its latest analysis.
- `/analyses/:analysisId/ask` — ask one evidence-backed question; the latest response is held only in page memory.

Feature-location answers render probable files, inferred role badges, confidence, direct and
indirect impact, likely tests, a structured plan, exact source links, and explicit limitations.
“Focus in graph” selects the matching persisted path on the existing dashboard; its query string
does not provide a trusted file ID. “Ask about this file” pre-fills a bounded impact question.

## Quality checks

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

Tests mock HTTP; no backend or AI provider is contacted.

## Known limitations

The API currently exposes repository metadata, analysis state, analysis history, and bounded repository Q&A. It does not expose analysis statistics or generated reports. Analysis progress is polled every two seconds while queued or running. There is no authentication, history, streaming, cancellation control, or frontend persistence.
