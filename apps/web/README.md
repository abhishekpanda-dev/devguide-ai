# DevGuide AI web

React frontend MVP for the existing DevGuide AI API. It displays only data returned by documented public endpoints; architecture summaries, health scores, language statistics, chat history, and streaming are not available.

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
