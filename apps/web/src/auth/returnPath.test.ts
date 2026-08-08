import { getSafeReturnPath } from './returnPath'

test('defaults to the repository submission route', () => {
  expect(getSafeReturnPath(undefined)).toBe('/repositories/new')
})

test.each(['/login', '/login?expired=1', '/register', 'https://example.com', '//example.com'])(
  'rejects unsafe or authentication return destination %s',
  (returnTo) => {
    expect(getSafeReturnPath({ returnTo })).toBe('/repositories/new')
  },
)

test('accepts an internal protected return destination', () => {
  expect(getSafeReturnPath({ returnTo: '/repositories/r1?tab=quality' })).toBe(
    '/repositories/r1?tab=quality',
  )
})
