import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { RepositorySubmitPage } from './RepositorySubmitPage'
import { validateRepositoryUrl } from './repositoryValidation'
import { renderRoute, jsonResponse, repository, analysis } from '../test/test-utils'

test('validates public GitHub repository URLs', () => {
  expect(validateRepositoryUrl('https://github.com/acme/project')).toBeNull()
  expect(validateRepositoryUrl('http://github.com/acme/project')).toMatch(/public GitHub/)
  expect(validateRepositoryUrl('https://gitlab.com/acme/project')).toMatch(/public GitHub/)
  expect(validateRepositoryUrl('not a url')).toMatch(/valid URL/)
})
test('submits and navigates with keyboard-accessible controls', async () => {
  const user = userEvent.setup()
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse({ repository, analysis_job: analysis }, 201),
  )
  renderRoute(
    <Routes>
      <Route path="/" element={<RepositorySubmitPage />} />
      <Route path="/analyses/:id" element={<h1>Progress</h1>} />
    </Routes>,
    '/',
    '*',
  )
  const input = screen.getByLabelText(/repository url/i)
  await user.type(input, repository.source_url)
  await user.tab()
  expect(screen.getByRole('button')).toHaveFocus()
  await user.keyboard('{Enter}')
  expect(await screen.findByRole('heading', { name: 'Progress' })).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledWith(
    expect.stringMatching(/\/api\/v1\/repositories$/),
    expect.objectContaining({ method: 'POST' }),
  )
})
test('shows API errors and correlation IDs', async () => {
  const user = userEvent.setup()
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    jsonResponse(
      {
        error: {
          code: 'validation_error',
          message: 'Repository rejected.',
          correlation_id: 'corr-1',
        },
      },
      422,
    ),
  )
  renderRoute(<RepositorySubmitPage />)
  await user.type(screen.getByLabelText(/repository url/i), repository.source_url)
  await user.click(screen.getByRole('button'))
  expect(await screen.findByText('Repository rejected.')).toBeInTheDocument()
  expect(screen.getByText(/corr-1/)).toBeInTheDocument()
})
test('rejects an empty submission without a request', async () => {
  const user = userEvent.setup()
  const fetchSpy = vi.spyOn(globalThis, 'fetch')
  renderRoute(<RepositorySubmitPage />)
  await user.click(screen.getByRole('button'))
  expect(screen.getByRole('alert')).toHaveTextContent(/valid URL/)
  await waitFor(() => expect(fetchSpy).not.toHaveBeenCalled())
})
