import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { vi } from 'vitest'
import { ProtectedRoute, PublicOnlyRoute } from './RouteGuards'

const authState = vi.hoisted(() => ({
  user: null as null | { id: string },
  isLoading: false,
  sessionError: null as string | null,
}))
vi.mock('./AuthContext', () => ({ useAuth: () => authState }))

beforeEach(() => {
  authState.user = null
  authState.isLoading = false
  authState.sessionError = null
})

test('protected routes redirect unauthenticated users', async () => {
  authState.user = null
  render(
    <MemoryRouter initialEntries={['/workspace']}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/workspace" element={<h1>Workspace</h1>} />
        </Route>
        <Route path="/login" element={<h1>Sign in</h1>} />
      </Routes>
    </MemoryRouter>,
  )
  expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
})

test('authenticated users enter protected routes and bypass sign in', async () => {
  authState.user = { id: 'u1' }
  const routes = (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route path="/workspace" element={<h1>Workspace</h1>} />
      </Route>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/sign-in" element={<h1>Sign in</h1>} />
      </Route>
      <Route path="/repositories/new" element={<h1>New repository</h1>} />
    </Routes>
  )
  const view = render(<MemoryRouter initialEntries={['/workspace']}>{routes}</MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'Workspace' })).toBeInTheDocument()
  view.unmount()
  render(<MemoryRouter initialEntries={['/sign-in']}>{routes}</MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'New repository' })).toBeInTheDocument()
})

test('route guards do not redirect while the startup session is loading', () => {
  authState.user = null
  authState.isLoading = true
  render(
    <MemoryRouter initialEntries={['/workspace']}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/workspace" element={<h1>Workspace</h1>} />
        </Route>
        <Route path="/login" element={<h1>Sign in</h1>} />
      </Routes>
    </MemoryRouter>,
  )
  expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
  expect(screen.queryByRole('heading', { name: 'Sign in' })).not.toBeInTheDocument()
  authState.isLoading = false
})

test('public auth routes also wait for session loading', () => {
  authState.user = { id: 'u1' }
  authState.isLoading = true
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<h1>Sign in</h1>} />
        </Route>
        <Route path="/repositories/new" element={<h1>New repository</h1>} />
      </Routes>
    </MemoryRouter>,
  )
  expect(screen.getByRole('status')).toBeInTheDocument()
  expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  authState.isLoading = false
})
