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
test('renders a successful answer and citation details', async () => {
  await ask()
  expect(await screen.findByText(/Authentication is implemented/)).toBeInTheDocument()
  expect(screen.getByText('app/auth.py')).toBeInTheDocument()
  expect(screen.getByText('Lines 1–4')).toBeInTheDocument()
  expect(screen.getByText(/chunk-12345/)).toBeInTheDocument()
  expect(screen.getByText(/mock-model/)).toBeInTheDocument()
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
