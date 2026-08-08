import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RepositoryDashboardPage } from './RepositoryDashboardPage'
import {
  analysis,
  analysisSummary,
  jsonResponse,
  renderRoute,
  repository,
} from '../test/test-utils'

const finding = {
  id: 'f1',
  rule_id: 'tls',
  severity: 'high',
  category: 'security',
  title: 'TLS verification disabled',
  explanation: 'A static call disables certificate verification.',
  path: 'app/client.py',
  start_line: 12,
  end_line: 12,
  evidence_excerpt: 'verify=False',
  deterministic_recommendation: 'Enable verification.',
  confidence: 1,
  content_hash: 'a'.repeat(64),
  commit_sha: 'b'.repeat(40),
  source_url: 'https://github.com/acme/project/blob/b/app/client.py#L12',
}
const file = {
  repository_file_id: 'file-1',
  path: 'app/main.py',
  language: 'python',
  classification: 'source',
  line_count: 20,
  content_hash: 'a'.repeat(64),
  commit_sha: 'b'.repeat(40),
  is_entry_point: true,
  entry_point_reason: 'Python main guard.',
  entry_point_confidence: 1,
  inbound_dependency_count: 0,
  outbound_dependency_count: 2,
  total_dependency_count: 2,
}
const findings = {
  analysis_job_id: 'a1',
  total_count: 3,
  returned_count: 1,
  severity_counts: { high: 1, warning: 1, info: 1 },
  limitations: [],
  findings: [finding],
}
const structure = {
  analysis_job_id: 'a1',
  repository: { id: 'r1', owner: 'acme', name: 'project', commit_sha: 'b'.repeat(40) },
  files: [file],
  dependency_edges: [],
  entry_points: [file],
  summary: {
    file_count: 12,
    directory_count: 3,
    language_counts: { python: 8, markdown: 4 },
    edge_count: 6,
    entry_point_count: 1,
    highest_inbound_files: [file],
    highest_outbound_files: [file],
    most_connected_files: [file],
  },
  limitations: [],
}
const quality = {
  analysis_job_id: 'a1',
  overall_score: 86,
  category_scores: { maintainability: 80, reliability: 90, security: 84, structure: 90 },
  score_breakdown: [
    {
      category: 'security',
      signal_type: 'high_findings',
      count: 1,
      points_deducted: 8,
      explanation: 'Capped static penalty.',
    },
  ],
  unused_code_candidates: [
    {
      id: 'u1',
      symbol_name: 'orphan',
      symbol_kind: 'function',
      path: 'app/unused.py',
      language: 'python',
      start_line: 2,
      end_line: 8,
      reason: 'No reference.',
      confidence: 0.9,
      recommendation: 'Review usage.',
      excerpt: 'def orphan(): pass',
      source_url: 'https://github.com/acme/project/blob/b/app/unused.py#L2-L8',
    },
  ],
  duplicate_code_groups: [
    {
      group_id: 'dup-1',
      match_type: 'exact_normalized',
      confidence: 1,
      recommendation: 'Extract shared code.',
      members: [],
    },
  ],
  summary: { unused_candidate_count: 1, duplicate_group_count: 1 },
  limitations: [],
  score_version: 'quality-v1',
}

function dashboardResponse(input: RequestInfo | URL) {
  const url = String(input)
  if (url.includes('/analyses/a1/summary')) return jsonResponse(analysisSummary)
  if (url.includes('/analyses/a1/findings')) return jsonResponse(findings)
  if (url.includes('/analyses/a1/structure')) return jsonResponse(structure)
  if (url.includes('/analyses/a1/quality')) return jsonResponse(quality)
  if (url.includes('/analyses?')) return jsonResponse({ items: [analysis], limit: 20, offset: 0 })
  return jsonResponse(repository)
}

test('renders the dark shell with real metrics, workspace data, links, and toolbar', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(dashboardResponse)
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(await screen.findByRole('heading', { name: 'project' })).toBeInTheDocument()
  expect(screen.getByTestId('dark-dashboard-shell')).toBeInTheDocument()
  expect(await screen.findByText('86')).toBeInTheDocument()
  expect(screen.getByText('Repository metrics')).toBeInTheDocument()
  expect(screen.getByText('Finding summary')).toBeInTheDocument()
  const languagesSection = screen.getByRole('region', { name: 'Languages' })
  expect(within(languagesSection).getByLabelText('python: 8 files')).toHaveTextContent('8 files')
  expect(within(languagesSection).queryByText(/analysis completed/i)).not.toBeInTheDocument()
  expect(within(languagesSection).queryByText(/^ready$/i)).not.toBeInTheDocument()
  expect(within(languagesSection).queryByText(/100% complete/i)).not.toBeInTheDocument()
  expect(screen.getByText('Python main guard. · 100%')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Dependency visualization' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Ask' })).toHaveAttribute('href', '/analyses/a1/ask')
  expect(screen.getAllByRole('link', { name: 'Quality' })[0]).toHaveAttribute(
    'href',
    '/analyses/a1/quality',
  )
  expect(screen.getAllByRole('link', { name: 'app/client.py:12' })[0]).toHaveAttribute(
    'href',
    finding.source_url,
  )
  expect(screen.getByRole('button', { name: /Tools/ })).toHaveTextContent('Planned')
})

test('uses the persisted active analysis id across dashboard findings and quality requests', async () => {
  const requested: string[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = String(input)
    requested.push(url)
    if (url.includes('/analyses?')) {
      return jsonResponse({
        items: [{ ...analysis, id: 'newer-analysis' }, analysis],
        limit: 20,
        offset: 0,
      })
    }
    return dashboardResponse(input)
  })

  renderRoute(
    <RepositoryDashboardPage />,
    '/repositories/r1?analysis=a1',
    '/repositories/:repositoryId',
  )

  expect(await screen.findByRole('link', { name: 'Ask' })).toHaveAttribute(
    'href',
    '/analyses/a1/ask',
  )
  expect(requested.some((url) => url.includes('/analyses/a1/findings'))).toBe(true)
  expect(requested.some((url) => url.includes('/analyses/a1/quality'))).toBe(true)
  expect(requested.some((url) => url.includes('/analyses/newer-analysis/'))).toBe(false)
})

test('renders a full-shell loading state', () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => undefined))
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(screen.getByRole('status')).toHaveTextContent('Loading intelligence workspace')
})

test('renders an empty repository-analysis state', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) =>
    String(input).includes('/analyses?')
      ? jsonResponse({ items: [], limit: 20, offset: 0 })
      : jsonResponse(repository),
  )
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(
    await screen.findByText('No completed or queued analysis is available for this repository.'),
  ).toBeInTheDocument()
})

test('degrades gracefully when an optional summary panel fails', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) =>
    String(input).includes('/summary')
      ? jsonResponse(
          {
            error: {
              code: 'analysis_not_ready',
              message: 'Parser statistics are unavailable.',
              correlation_id: 'summary-1',
            },
          },
          409,
        )
      : dashboardResponse(input),
  )
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  expect(await screen.findByText('Parser statistics are unavailable.')).toBeInTheDocument()
  expect(screen.getByText(/summary-1/)).toBeInTheDocument()
  expect(screen.getByText('Python main guard. · 100%')).toBeInTheDocument()
})

test('renders a full repository error safely', async () => {
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

test('supports keyboard-operable tabs and collapsible panel controls', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(dashboardResponse)
  const user = userEvent.setup()
  renderRoute(<RepositoryDashboardPage />, '/repositories/r1', '/repositories/:repositoryId')
  const qualityTab = await screen.findByRole('tab', { name: 'quality' })
  await user.click(qualityTab)
  expect(qualityTab).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByText('Unused-code candidate: orphan')).toBeInTheDocument()
  const toggle = screen.getByRole('button', { name: 'Repository summary' })
  await user.click(toggle)
  expect(toggle).toHaveAttribute('aria-expanded', 'true')
})
