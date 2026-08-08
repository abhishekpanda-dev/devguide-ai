import { afterEach, vi } from 'vitest'
import { currentUser, login } from './auth'

afterEach(() => vi.restoreAllMocks())

test('login posts credentials and current-user follows through the same-origin session client', async () => {
  const user = { id: 'u1', email: 'person@example.com', created_at: '2026-01-01T00:00:00Z' }
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({ user }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ user }), { status: 200 }))

  await login('person@example.com', 'private-password')
  const response = await currentUser()

  expect(response.user).toEqual(user)
  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    '/api/v1/auth/login',
    expect.objectContaining({ method: 'POST', credentials: 'include' }),
  )
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    '/api/v1/auth/me',
    expect.objectContaining({ credentials: 'include' }),
  )
})
