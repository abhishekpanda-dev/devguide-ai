import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { LoginPage } from './LoginPage'
import { renderRoute } from '../test/test-utils'
import { ApiError } from '../api/client'

const loginMock = vi.hoisted(() => vi.fn())
const navigateMock = vi.hoisted(() => vi.fn())
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ login: loginMock }) }))
vi.mock('react-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router')>()),
  useNavigate: () => navigateMock,
}))

beforeEach(() => {
  loginMock.mockReset()
  navigateMock.mockReset()
  localStorage.clear()
  sessionStorage.clear()
})

test('renders branded login controls and a credential-safe interactive preview', async () => {
  const user = userEvent.setup()
  renderRoute(<LoginPage />, '/sign-in', '/sign-in')
  const logo = screen.getByRole('img', { name: 'DevGuide AI — Build, Learn, Ship' })
  expect(logo).toHaveAttribute('src', '/devguide-logo.png')
  expect(logo).toHaveClass('authBrandLogo')
  expect(logo.closest('header')).toHaveClass('authBrandHeader')
  expect(screen.queryByText('BUILD • LEARN • SHIP')).not.toBeInTheDocument()
  const heading = screen.getByRole('heading', { name: 'Welcome back' })
  expect(heading).toBeInTheDocument()
  expect(heading.closest('form')?.parentElement).toHaveClass('authFormColumn')
  const preview = screen.getByLabelText('Interactive authentication request preview')
  const output = screen.getByLabelText('Authentication status preview')
  expect(preview.parentElement).toHaveClass('authPreviewGrid')
  expect(output.parentElement).toBe(preview.parentElement)
  expect(preview).toHaveTextContent('LIVE CODE PREVIEW')
  expect(output).toHaveTextContent('TEST OUTPUT')
  expect(preview).toHaveTextContent('email_received = False')
  expect(preview).toHaveTextContent('password_received = False')
  await user.type(screen.getByLabelText('Email'), 'private@example.com')
  await user.type(screen.getByLabelText('Password'), 'never-show-this')
  expect(preview).toHaveTextContent('email_received = True')
  expect(preview).toHaveTextContent('password_received = True')
  expect(preview).toHaveTextContent('request_ready = True')
  expect(output).toHaveTextContent('Email field received')
  expect(output).toHaveTextContent('Password field received')
  expect(output).toHaveTextContent('Request ready')
  expect(preview).not.toHaveTextContent('private@example.com')
  expect(preview).not.toHaveTextContent('never-show-this')
  await user.click(screen.getByRole('button', { name: 'Show password' }))
  expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text')
})

test('validates, submits through AuthContext, and shows a generic failure', async () => {
  const user = userEvent.setup()
  renderRoute(<LoginPage />, '/sign-in', '/sign-in')
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
  await user.type(screen.getByLabelText('Email'), 'person@example.com')
  await user.type(screen.getByLabelText('Password'), 'private-password')
  loginMock.mockRejectedValueOnce(
    new ApiError('Email or password is incorrect.', 'invalid_credentials', 'ref-1', 401),
  )
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is incorrect.')
  expect(screen.getByLabelText('Authentication status preview')).toHaveTextContent(
    'Authentication rejected',
  )
  expect(loginMock).toHaveBeenCalledWith('person@example.com', 'private-password')
})

test('tab switches do not remount the form, clear credentials, or persist the password', async () => {
  const user = userEvent.setup()
  renderRoute(<LoginPage />, '/login', '/login')
  const email = screen.getByLabelText('Email')
  const password = screen.getByLabelText('Password')
  await user.type(email, 'testuser@example.com')
  await user.type(password, 'StrongPassword123!')

  document.dispatchEvent(new Event('visibilitychange'))
  window.dispatchEvent(new Event('focus'))

  expect(email).toHaveValue('testuser@example.com')
  expect(password).toHaveValue('StrongPassword123!')
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
  expect(window.location.href).not.toContain('StrongPassword123!')
  expect(loginMock).not.toHaveBeenCalled()
})

test('successful login clears the password and navigates exactly once after auth resolves', async () => {
  const user = userEvent.setup()
  loginMock.mockResolvedValue({
    id: 'u1',
    email: 'testuser@example.com',
    created_at: '2026-01-01T00:00:00Z',
  })
  renderRoute(<LoginPage />, '/login', '/login')
  await user.type(screen.getByLabelText('Email'), 'testuser@example.com')
  await user.type(screen.getByLabelText('Password'), 'StrongPassword123!')

  await user.click(screen.getByRole('button', { name: 'Sign in' }))

  expect(loginMock).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('Password')).toHaveValue('')
  expect(navigateMock).toHaveBeenCalledOnce()
  expect(navigateMock).toHaveBeenCalledWith('/repositories/new', { replace: true })
})
