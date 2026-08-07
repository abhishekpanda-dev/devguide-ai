import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import type { ReactNode } from 'react'
export function renderRoute(ui: ReactNode, route = '/', path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
export const jsonResponse = (data: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } }),
  )
export const analysis = {
  id: 'a1',
  repository_id: 'r1',
  status: 'completed',
  current_stage: 'repository_parsing',
  progress_percent: 100,
  pipeline_version: '1',
  error_code: null,
  error_message: null,
  started_at: null,
  completed_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
} as const
export const repository = {
  id: 'r1',
  source_type: 'github_public',
  source_url: 'https://github.com/acme/project',
  normalized_url: 'https://github.com/acme/project',
  owner: 'acme',
  name: 'project',
  default_branch: 'main',
  latest_commit_sha: 'abc123',
  status: 'ready',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
} as const
export const analysisSummary = {
  analysis_job_id: 'a1',
  files_analyzed: 12,
  chunks_created: 24,
  languages: [
    { language: 'python', file_count: 8, line_count: 320 },
    { language: 'markdown', file_count: 4, line_count: 80 },
  ],
  total_lines: 400,
  test_file_count: 3,
  documentation_file_count: 4,
  skipped_file_count: 2,
  limitations: ['vendor/: directory was skipped.'],
} as const
