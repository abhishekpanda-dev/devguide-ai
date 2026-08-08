import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeFindingsPage } from './CodeFindingsPage'
import { jsonResponse, renderRoute } from '../test/test-utils'
const finding = {
  id: 'f1',
  rule_id: 'security.hardcoded-credential',
  severity: 'high',
  category: 'security',
  title: 'Possible hardcoded credential',
  explanation: 'A credential-like variable is assigned a literal source value.',
  path: 'src/config.py',
  start_line: 27,
  end_line: 27,
  evidence_excerpt: 'API_KEY = "[REDACTED]"',
  deterministic_recommendation: 'Load it from an environment variable or secret manager.',
  confidence: 0.9,
  content_hash: 'a'.repeat(64),
  commit_sha: 'b'.repeat(40),
  source_url: `https://github.com/acme/project/blob/${'b'.repeat(40)}/src/config.py#L27`,
}
const response = {
  analysis_job_id: 'a1',
  total_count: 1,
  returned_count: 1,
  findings: [finding],
  limitations: [],
  severity_counts: { high: 1, warning: 0, info: 0 },
}
test('renders finding details counts labels and exact GitHub link', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(response))
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  expect(await screen.findByText('Possible hardcoded credential')).toBeInTheDocument()
  expect(screen.getByText('API_KEY = "[REDACTED]"')).toBeInTheDocument()
  expect(screen.getByText('Suggested action')).toBeInTheDocument()
  expect(screen.getAllByText('high').length).toBeGreaterThan(0)
  const link = screen.getByRole('link', { name: /Open on GitHub/ })
  expect(link).toHaveAttribute('href', finding.source_url)
  expect(link).toHaveAttribute('target', '_blank')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
})
test('supports accessible severity and category filters', async () => {
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(response))
  const user = userEvent.setup()
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  await screen.findByText('Possible hardcoded credential')
  await user.selectOptions(screen.getByLabelText('Severity'), 'high')
  await user.selectOptions(screen.getByLabelText('Category'), 'security')
  expect(spy.mock.calls.some(([url]) => String(url).includes('severity=high'))).toBe(true)
  expect(spy.mock.calls.some(([url]) => String(url).includes('category=security'))).toBe(true)
})
test('renders loading state', () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => undefined))
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  expect(screen.getByRole('status')).toHaveTextContent('Analyzing repository findings...')
})
test('renders empty state', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse({
      ...response,
      total_count: 0,
      returned_count: 0,
      findings: [],
      severity_counts: { high: 0, warning: 0, info: 0 },
    }),
  )
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  expect(
    await screen.findByText('No persisted findings were detected for this analysis.'),
  ).toBeInTheDocument()
})
test('renders safe API error with correlation ID', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse(
      {
        error: {
          code: 'analysis_not_ready',
          message: 'Code findings are not ready.',
          correlation_id: 'find-1',
        },
      },
      409,
    ),
  )
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  expect(await screen.findByText('Code findings are not ready.')).toBeInTheDocument()
  expect(screen.getByText(/find-1/)).toBeInTheDocument()
})

test('generates an advisory fix only after click and renders trusted details', async () => {
  const user = userEvent.setup()
  const suggested = {
    analysis_job_id: 'a1',
    finding_id: 'f1',
    rule_id: finding.rule_id,
    explanation: 'The literal should not remain in source.',
    probable_fix: 'Read it from the environment.',
    example_code: 'API_KEY = os.environ["API_KEY"]',
    citations: [
      {
        path: finding.path,
        start_line: 27,
        end_line: 27,
        content_hash: finding.content_hash,
        source_url: finding.source_url,
      },
    ],
    provider: 'mock',
    model: 'mock-suggested-fix-v1',
    limitations: ['Review in context.'],
    correlation_id: 'fix-1',
  }
  const spy = vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation((url) =>
      String(url).endsWith('/suggested-fix') ? jsonResponse(suggested) : jsonResponse(response),
    )
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  const button = await screen.findByRole('button', { name: 'Generate probable fix' })
  expect(screen.queryByLabelText('AI suggested fix')).not.toBeInTheDocument()
  await user.click(button)
  expect(await screen.findByText(suggested.explanation)).toBeInTheDocument()
  expect(screen.getByText(suggested.probable_fix)).toBeInTheDocument()
  expect(screen.getByText(suggested.example_code)).toBeInTheDocument()
  expect(screen.getByText(/mock-suggested-fix-v1/)).toBeInTheDocument()
  expect(screen.getByText('Review before applying.')).toBeInTheDocument()
  expect(spy.mock.calls.filter(([url]) => String(url).endsWith('/suggested-fix'))).toHaveLength(1)
})

test('shows loading, prevents duplicate clicks, and allows retry after a safe error', async () => {
  const user = userEvent.setup()
  let resolveRequest: ((value: Response) => void) | undefined
  let attempts = 0
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    if (!String(url).endsWith('/suggested-fix')) return jsonResponse(response)
    attempts += 1
    if (attempts === 1)
      return Promise.resolve(
        jsonResponse(
          {
            error: {
              code: 'ai_provider_timeout',
              message: 'The AI provider request timed out.',
              correlation_id: 'fix-timeout',
            },
          },
          504,
        ),
      )
    return new Promise((resolve) => {
      resolveRequest = resolve
    })
  })
  renderRoute(<CodeFindingsPage />, '/analyses/a1/findings', '/analyses/:analysisId/findings')
  await user.click(await screen.findByRole('button', { name: 'Generate probable fix' }))
  expect(await screen.findByText(/fix-timeout/)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Retry' }))
  const loading = screen.getByRole('button', { name: 'Generating probable fix...' })
  expect(loading).toBeDisabled()
  await user.click(loading)
  expect(attempts).toBe(2)
  resolveRequest?.(await jsonResponse({}))
})
