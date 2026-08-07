import { screen } from '@testing-library/react'
import { jsonResponse, renderRoute } from '../test/test-utils'
import { RepositoryQualityPage } from './RepositoryQualityPage'

const payload = {
  analysis_job_id: 'analysis-1', overall_score: 84,
  category_scores: { maintainability: 80, reliability: 90, security: 100, structure: 66 },
  score_breakdown: [{ category: 'maintainability', signal_type: 'unused_candidates', count: 2, points_deducted: 2, explanation: 'Static candidates require review.' }],
  unused_code_candidates: [{ id: 'unused-1', symbol_name: 'orphan', symbol_kind: 'function', path: 'app/a.py', language: 'python', start_line: 3, end_line: 8, reason: 'No persisted lexical reference.', confidence: 0.9, recommendation: 'Review dynamic usage.', excerpt: 'def orphan(): pass', source_url: 'https://github.com/acme/repo/blob/abc/app/a.py#L3-L8' }],
  duplicate_code_groups: [{ group_id: 'dup-1', match_type: 'exact_normalized', confidence: 1, recommendation: 'Extract shared code.', members: [{ path: 'app/a.py', language: 'python', start_line: 3, end_line: 8, excerpt: 'x', source_url: 'https://github.com/acme/repo/blob/abc/app/a.py#L3-L8' }, { path: 'app/b.py', language: 'python', start_line: 4, end_line: 9, excerpt: 'x', source_url: 'https://github.com/acme/repo/blob/abc/app/b.py#L4-L9' }] }],
  summary: { unused_candidate_count: 1, duplicate_group_count: 1 }, limitations: ['Dynamic references may be missed.'], score_version: 'quality-v1',
}

test('renders score categories deductions candidates duplicates and exact links', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(payload))
  renderRoute(<RepositoryQualityPage />, '/analyses/analysis-1/quality', '/analyses/:analysisId/quality')
  expect(await screen.findByText('84')).toBeInTheDocument()
  expect(screen.getByText('Candidate:', { exact: false })).toBeInTheDocument()
  expect(screen.getByText('Candidate group dup-1')).toBeInTheDocument()
  expect(screen.getAllByRole('link', { name: 'app/a.py:3-8' })[0]).toHaveAttribute('href', payload.unused_code_candidates[0].source_url)
  expect(screen.getByText('Dynamic references may be missed.')).toBeInTheDocument()
})

test('renders loading, empty and API error states', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse({ ...payload, score_breakdown: [], unused_code_candidates: [], duplicate_code_groups: [] }))
  renderRoute(<RepositoryQualityPage />, '/analyses/analysis-1/quality', '/analyses/:analysisId/quality')
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  expect(await screen.findByText('No unused-code candidates')).toBeInTheDocument()
  expect(screen.getByText('No duplicate-code candidates')).toBeInTheDocument()
})

test('renders a safe API error', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse(
      {
        error: {
          code: 'analysis_not_ready',
          message: 'Quality intelligence is not ready.',
          correlation_id: 'quality-1',
        },
      },
      409,
    ),
  )
  renderRoute(
    <RepositoryQualityPage />,
    '/analyses/analysis-1/quality',
    '/analyses/:analysisId/quality',
  )
  expect(await screen.findByText('Quality intelligence is not ready.')).toBeInTheDocument()
  expect(screen.getByText(/quality-1/)).toBeInTheDocument()
})
