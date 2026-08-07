import { screen } from '@testing-library/react'
import { RepositoryDashboardPage } from './RepositoryDashboardPage'
import { analysis, jsonResponse, renderRoute, repository } from '../test/test-utils'

test('renders repository facts and latest analysis without unsupported metrics', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) =>
    String(input).includes('/analyses?')
      ? jsonResponse({ items: [analysis], limit: 20, offset: 0 })
      : jsonResponse(repository),
  )
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(await screen.findByRole('heading', { name: 'project' })).toBeInTheDocument()
  expect(screen.getByText('abc123')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: /health score/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: /language statistics/i })).not.toBeInTheDocument()
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
