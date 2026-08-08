import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, vi } from 'vitest'
import { ApiError } from '../api/client'
import { AuthProvider, useAuth } from './AuthContext'
import { resetStartupSessionForTests } from './sessionBootstrap'

const api = vi.hoisted(() => ({
  currentUser: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../api/auth', () => ({
  currentUser: api.currentUser,
  login: api.login,
  register: api.register,
  logout: api.logout,
}))

const existingUser = {
  id: 'u1',
  email: 'existing@example.com',
  created_at: '2026-01-01T00:00:00Z',
}
const signedInUser = {
  id: 'u2',
  email: 'signed-in@example.com',
  created_at: '2026-01-02T00:00:00Z',
}

function Probe() {
  const auth = useAuth()
  const runLogin = () => {
    void auth.login('signed-in@example.com', 'private-password').catch(() => undefined)
  }
  return (
    <div>
      <span data-testid="user">{auth.user?.email ?? 'none'}</span>
      <span data-testid="loading">{String(auth.isLoading)}</span>
      <span data-testid="error">{auth.sessionError ?? 'none'}</span>
      <button type="button" onClick={runLogin}>
        Login
      </button>
    </div>
  )
}

beforeEach(() => {
  resetStartupSessionForTests()
  vi.clearAllMocks()
})

test('checks the session once at startup and not again on focus or visibility changes', async () => {
  api.currentUser.mockResolvedValue({ user: existingUser })
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  expect(await screen.findByText(existingUser.email)).toBeInTheDocument()

  act(() => {
    document.dispatchEvent(new Event('visibilitychange'))
    window.dispatchEvent(new Event('focus'))
  })

  expect(api.currentUser).toHaveBeenCalledTimes(1)
  expect(screen.getByTestId('user')).toHaveTextContent(existingUser.email)
})

test('login fetches the current user and updates state before its promise resolves', async () => {
  const events: string[] = []
  api.currentUser.mockResolvedValueOnce({ user: existingUser }).mockImplementationOnce(async () => {
    events.push('me')
    return { user: signedInUser }
  })
  api.login.mockImplementation(async () => {
    events.push('login')
    return { user: signedInUser }
  })
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  await screen.findByText(existingUser.email)

  await userEvent.click(screen.getByRole('button', { name: 'Login' }))

  await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(signedInUser.email))
  expect(screen.getByTestId('loading')).toHaveTextContent('false')
  expect(events).toEqual(['login', 'me'])
})

test('a temporary auth/me error retains the existing authenticated user', async () => {
  api.currentUser
    .mockResolvedValueOnce({ user: existingUser })
    .mockRejectedValueOnce(new ApiError('Offline', 'network_error'))
  api.login.mockResolvedValue({ user: signedInUser })
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  await screen.findByText(existingUser.email)

  await userEvent.click(screen.getByRole('button', { name: 'Login' }))

  await waitFor(() => expect(screen.getByTestId('error')).not.toHaveTextContent('none'))
  expect(screen.getByTestId('user')).toHaveTextContent(existingUser.email)
})

test('an auth/me 401 clears the authenticated user', async () => {
  api.currentUser
    .mockResolvedValueOnce({ user: existingUser })
    .mockRejectedValueOnce(new ApiError('Unauthorized', 'unauthorized', undefined, 401))
  api.login.mockResolvedValue({ user: signedInUser })
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  await screen.findByText(existingUser.email)

  await userEvent.click(screen.getByRole('button', { name: 'Login' }))

  await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('none'))
})
