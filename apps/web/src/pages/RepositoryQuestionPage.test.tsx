import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RepositoryQuestionPage } from './RepositoryQuestionPage'
import { jsonResponse, renderRoute } from '../test/test-utils'

const response = {
  analysis_job_id: 'a1',
  question: 'Where?',
  answer: 'Authentication is implemented in the auth module.',
  citations: [
    {
      chunk_id: 'chunk-1234567890',
      repository_file_id: 'f1',
      path: 'app/auth.py',
      start_line: 1,
      end_line: 4,
      content_hash: 'abc',
    },
  ],
  insufficient_evidence: false,
  evidence_quality: 'high',
  retrieved_evidence_count: 1,
  provider: 'mock',
  model: 'mock-model',
  limitations: [],
  correlation_id: 'corr-q',
}
async function ask(mockResponse: unknown = response, status = 200) {
  const user = userEvent.setup()
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(mockResponse, status))
  renderRoute(<RepositoryQuestionPage />, '/analyses/a1/ask', '/analyses/:analysisId/ask')
  await user.type(screen.getByLabelText('Question'), 'Where?')
  await user.click(screen.getByRole('button', { name: 'Ask DevGuide' }))
  return user
}
test('validates the question form', async () => {
  const user = userEvent.setup()
  const spy = vi.spyOn(globalThis, 'fetch')
  renderRoute(<RepositoryQuestionPage />, '/analyses/a1/ask', '/analyses/:analysisId/ask')
  await user.click(screen.getByRole('button', { name: 'Ask DevGuide' }))
  expect(screen.getByRole('alert')).toHaveTextContent(/Enter a question/)
  expect(spy).not.toHaveBeenCalled()
})
test('shows repository evidence loading copy while the grounded request is pending', async () => {
  const user = userEvent.setup()
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => undefined))
  renderRoute(<RepositoryQuestionPage />, '/analyses/a1/ask', '/analyses/:analysisId/ask')
  await user.type(screen.getByLabelText('Question'), 'How is authentication structured?')
  await user.click(screen.getByRole('button', { name: 'Ask DevGuide' }))
  expect(screen.getByRole('button')).toHaveTextContent('Analyzing repository evidence…')
})
test('renders a successful answer and citation details', async () => {
  await ask()
  expect(await screen.findByText(/Authentication is implemented/)).toBeInTheDocument()
  expect(screen.getByText('app/auth.py')).toBeInTheDocument()
  expect(screen.getByText('Lines 1–4')).toBeInTheDocument()
  expect(screen.getByText(/chunk-12345/)).toBeInTheDocument()
  expect(screen.getByText(/mock-model/)).toBeInTheDocument()
})
test('renders a probable structured change-impact answer with trusted actions', async () => {
  const featureFile = {
    repository_file_id: 'f1',
    path: 'app/auth.py',
    role: 'service',
    role_inferred: true,
    confidence: 0.82,
    reason: 'Exact filename and lexical matches.',
    source_url: 'https://github.com/acme/project/blob/abc/app/auth.py#L1-L4',
    evidence: ['Exact filename match.'],
    impact_kind: null,
  }
  await ask({
    ...response,
    feature_location: {
      feature_location_used: true,
      intent: 'change_impact',
      feature_phrase: 'authentication',
      likely_files: [featureFile],
      impact_summary: {
        direct_dependencies: [
          {
            ...featureFile,
            repository_file_id: 'f2',
            path: 'app/users.py',
            impact_kind: 'direct_static',
          },
        ],
        direct_dependents: [],
        probable_indirect: [
          {
            ...featureFile,
            repository_file_id: 'f3',
            path: 'app/session.py',
            impact_kind: 'probable_indirect',
          },
        ],
        probable_entry_points: [],
        related_findings: [],
        related_quality_candidates: [],
        unknown_dynamic_impact: 'Dynamic registration cannot be confirmed.',
      },
      related_tests: [
        {
          ...featureFile,
          repository_file_id: 't1',
          path: 'tests/test_auth.py',
          role: 'test',
          impact_kind: 'probable_indirect',
          reason: 'Likely by filename; coverage is not proven.',
        },
      ],
      change_plan: {
        start_here: ['app/auth.py'],
        inspect_files: ['app/auth.py'],
        likely_code_path: ['app/auth.py', 'app/users.py'],
        potentially_affected_files: ['app/users.py'],
        tests_to_review: ['tests/test_auth.py'],
        risks_and_limitations: ['Static evidence only.'],
      },
      limitations: ['Results are probable.'],
    },
  })
  expect(await screen.findByText(/Change-impact plan for/)).toBeInTheDocument()
  expect(screen.getAllByText('service (inferred)').length).toBeGreaterThan(0)
  expect(screen.getAllByText('82% probable').length).toBeGreaterThan(0)
  expect(screen.getByRole('heading', { name: 'Direct static impact' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Probable indirect impact' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: /Likely tests to inspect/ })).toBeInTheDocument()
  expect(screen.getAllByRole('link', { name: 'Focus in graph' })[0]).toHaveAttribute(
    'href',
    '/analyses/a1?focus=app%2Fauth.py',
  )
  expect(screen.getAllByRole('link', { name: 'Open exact source' })[0]).toHaveAttribute(
    'href',
    featureFile.source_url,
  )
  expect(screen.getByText(/coverage is not proven/)).toBeInTheDocument()
})
test('renders insufficient evidence and limitations', async () => {
  await ask({
    ...response,
    answer: '',
    citations: [],
    insufficient_evidence: true,
    evidence_quality: 'insufficient',
    provider: null,
    model: null,
    limitations: ['No matching lexical evidence.'],
  })
  expect(await screen.findByRole('heading', { name: 'Insufficient evidence' })).toBeInTheDocument()
  expect(screen.getByText('No matching lexical evidence.')).toBeInTheDocument()
})
test('renders question API errors with correlation ID', async () => {
  await ask(
    {
      error: {
        code: 'repository_question_failed',
        message: 'The repository question could not be completed.',
        correlation_id: 'question-ref',
      },
    },
    502,
  )
  expect(
    await screen.findByText('The repository question could not be completed.'),
  ).toBeInTheDocument()
  expect(screen.getByText(/question-ref/)).toBeInTheDocument()
})
test('submits bounded advanced retrieval controls', async () => {
  const user = userEvent.setup()
  const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(response))
  renderRoute(<RepositoryQuestionPage />, '/analyses/a1/ask', '/analyses/:analysisId/ask')
  await user.type(screen.getByLabelText('Question'), 'Where?')
  await user.click(screen.getByText('Advanced retrieval controls'))
  await user.type(screen.getByLabelText(/Language filters/), 'python, typescript')
  await user.type(screen.getByLabelText(/Path prefix/), 'apps/api')
  await user.click(screen.getByRole('button', { name: 'Ask DevGuide' }))
  const request = fetchSpy.mock.calls[0]?.[1]
  expect(JSON.parse(String(request?.body))).toMatchObject({
    language_filters: ['python', 'typescript'],
    path_prefix: 'apps/api',
    retrieval_limit: 10,
    retrieval_minimum_score: 1,
    maximum_citations: 10,
  })
})
