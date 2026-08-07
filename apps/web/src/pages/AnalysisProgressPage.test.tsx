import { screen } from '@testing-library/react'
import { AnalysisProgressPage } from './AnalysisProgressPage'
import { dashboardFocusTarget } from './analysisNavigation'
import { analysis, jsonResponse, renderRoute } from '../test/test-utils'

test('shows an explicit analysis loading state', () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => undefined))
  renderRoute(<AnalysisProgressPage />, '/analyses/a1', '/analyses/:analysisId')
  expect(screen.getByRole('status')).toHaveTextContent('Loading analysis status')
})
test('shows an explicit network failure state', async () => {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
  renderRoute(<AnalysisProgressPage />, '/analyses/a1', '/analyses/:analysisId')
  expect(await screen.findByText(/Unable to reach DevGuide AI/)).toBeInTheDocument()
})
test('renders analysis progress', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse({ ...analysis, status: 'running', progress_percent: 40 }),
  )
  renderRoute(<AnalysisProgressPage />, '/analyses/a1', '/analyses/:analysisId')
  expect((await screen.findAllByText('40%')).length).toBeGreaterThan(0)
  expect(screen.getByText('repository parsing')).toBeInTheDocument()
})
test('stops polling after a terminal status', async () => {
  const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(analysis))
  renderRoute(<AnalysisProgressPage />, '/analyses/a1', '/analyses/:analysisId')
  await screen.findByText('completed')
  await new Promise((resolve) => setTimeout(resolve, 2100))
  expect(fetchSpy).toHaveBeenCalledTimes(1)
})
test('renders a safe terminal analysis error', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse({ ...analysis, status: 'failed', error_message: 'Repository parsing failed.' }),
  )
  renderRoute(<AnalysisProgressPage />, '/analyses/a1', '/analyses/:analysisId')
  expect(await screen.findByRole('alert')).toHaveTextContent('Repository parsing failed.')
})

test('preserves a persisted-path focus request when handing off to the repository dashboard', () => {
  expect(dashboardFocusTarget('r1', '?focus=monitoring-dashboard%2Fsrc%2Frealtime.ts')).toBe(
    '/repositories/r1?focus=monitoring-dashboard%2Fsrc%2Frealtime.ts',
  )
  expect(dashboardFocusTarget('r1', '')).toBeNull()
})
