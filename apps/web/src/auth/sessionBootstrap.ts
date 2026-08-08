import { currentUser } from '../api/auth'

let startupSession: ReturnType<typeof currentUser> | null = null

export function getStartupSession() {
  startupSession ??= currentUser()
  return startupSession
}

export function resetStartupSessionForTests() {
  startupSession = null
}
