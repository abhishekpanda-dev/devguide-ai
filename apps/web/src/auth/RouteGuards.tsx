import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from './AuthContext'

export function SessionLoadingState() {
  return (
    <div className="sessionLoading" role="status">
      Checking your session…
    </div>
  )
}

function SessionRecoveryState({ message }: { message: string }) {
  return (
    <div className="sessionLoading" role="alert">
      {message}
    </div>
  )
}

export function ProtectedRoute() {
  const { user, isLoading, sessionError } = useAuth()
  const location = useLocation()
  if (isLoading) return <SessionLoadingState />
  if (sessionError && !user) return <SessionRecoveryState message={sessionError} />
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ returnTo: `${location.pathname}${location.search}` }}
      />
    )
  }
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { user, isLoading } = useAuth()
  if (isLoading) return <SessionLoadingState />
  return user ? <Navigate to="/repositories/new" replace /> : <Outlet />
}
