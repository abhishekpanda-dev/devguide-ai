const defaultAuthenticatedPath = '/repositories/new'
const authPaths = new Set(['/login', '/register', '/sign-in', '/sign-up'])

export function getSafeReturnPath(state: unknown): string {
  if (!state || typeof state !== 'object' || !('returnTo' in state)) {
    return defaultAuthenticatedPath
  }
  const returnTo = (state as { returnTo?: unknown }).returnTo
  if (typeof returnTo !== 'string' || !returnTo.startsWith('/') || returnTo.startsWith('//')) {
    return defaultAuthenticatedPath
  }
  const pathname = returnTo.split(/[?#]/, 1)[0]
  if (authPaths.has(pathname)) return defaultAuthenticatedPath
  return returnTo
}
