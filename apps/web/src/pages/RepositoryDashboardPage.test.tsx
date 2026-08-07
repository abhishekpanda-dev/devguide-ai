import { screen } from '@testing-library/react'
import { RepositoryDashboardPage } from './RepositoryDashboardPage'
import {
  analysis,
  analysisSummary,
  jsonResponse,
  renderRoute,
  repository,
} from '../test/test-utils'

function dashboardResponse(input: RequestInfo | URL) {
  const url = String(input)
  if (url.includes('/analyses/a1/summary')) return jsonResponse(analysisSummary)
  if (url.includes('/analyses?')) return jsonResponse({ items: [analysis], limit: 20, offset: 0 })
  return jsonResponse(repository)
}

test('renders real persisted repository statistics and parser limitations', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(dashboardResponse)
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')

  expect(await screen.findByRole('heading', { name: 'project' })).toBeInTheDocument()
  expect(await screen.findByText('Files analyzed')).toBeInTheDocument()
  expect(screen.getByText('12')).toBeInTheDocument()
  expect(screen.getByText('Evidence chunks')).toBeInTheDocument()
  expect(screen.getByText('24')).toBeInTheDocument()
  expect(screen.getByText('Total lines')).toBeInTheDocument()
  expect(screen.getByText('400')).toBeInTheDocument()
  expect(screen.getByText('Test files')).toBeInTheDocument()
  expect(screen.getByText('Documentation files')).toBeInTheDocument()
  expect(screen.getByText('Skipped files')).toBeInTheDocument()
  expect(screen.getByText('python')).toBeInTheDocument()
  expect(screen.getByText('markdown')).toBeInTheDocument()
  expect(screen.getByText('vendor/: directory was skipped.')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: /health score/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: /architecture/i })).not.toBeInTheDocument()
})

test('renders an analysis statistics loading state', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/analyses/a1/summary')) return new Promise(() => undefined)
    return dashboardResponse(input)
  })
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(await screen.findByText('Loading analysis statistics…')).toBeInTheDocument()
})

test('renders an empty statistics state', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/analyses/a1/summary'))
      return jsonResponse({
        ...analysisSummary,
        files_analyzed: 0,
        chunks_created: 0,
        languages: [],
        total_lines: 0,
        test_file_count: 0,
        documentation_file_count: 0,
      })
    return dashboardResponse(input)
  })
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(await screen.findByRole('heading', { name: 'No analyzed files' })).toBeInTheDocument()
  expect(screen.getByText('No supported languages were detected.')).toBeInTheDocument()
})

test('renders an analysis statistics API error', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/analyses/a1/summary'))
      return jsonResponse(
        {
          error: {
            code: 'analysis_not_ready',
            message: 'Parser statistics are not available for this analysis yet.',
            correlation_id: 'summary-1',
          },
        },
        409,
      )
    return dashboardResponse(input)
  })
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(
    await screen.findByText('Parser statistics are not available for this analysis yet.'),
  ).toBeInTheDocument()
  expect(screen.getByText(/summary-1/)).toBeInTheDocument()
})

test('renders a missing repository error', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) =>
    String(input).includes('/analyses?')
      ? jsonResponse({ items: [], limit: 20, offset: 0 })
      : jsonResponse(
          {
            error: {
              code: 'repository_not_found',
              message: 'The repository was not found.',
              correlation_id: 'missing-1',
            },
          },
          404,
        ),
  )
  renderRoute(<RepositoryDashboardPage />, '/repositories/missing', '/repositories/:repositoryId')
  expect(await screen.findByText('The repository was not found.')).toBeInTheDocument()
  expect(screen.getByText(/missing-1/)).toBeInTheDocument()
})
