import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { flushSync } from 'react-dom'
import {
  currentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type AuthUser,
} from '../api/auth'
import { ApiError } from '../api/client'
import { getStartupSession } from './sessionBootstrap'

interface AuthState {
  user: AuthUser | null
  isLoading: boolean
  sessionError: string | null
  login: (email: string, password: string) => Promise<AuthUser>
  register: (email: string, password: string, confirmPassword: string) => Promise<AuthUser>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [sessionError, setSessionError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getStartupSession()
      .then((response) => {
        if (active) setUser(response.user)
      })
      .catch((error: unknown) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) setUser(null)
        else setSessionError('Your session could not be checked. Please try again shortly.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    setSessionError(null)
    try {
      await loginRequest(email, password)
      const response = await currentUser()
      flushSync(() => {
        setUser(response.user)
        setSessionError(null)
        setIsLoading(false)
      })
      return response.user
    } catch (error) {
      flushSync(() => {
        if (error instanceof ApiError && error.status === 401) setUser(null)
        else setSessionError('Your session could not be refreshed. Please try again.')
        setIsLoading(false)
      })
      throw error
    }
  }

  const register = async (email: string, password: string, confirmPassword: string) => {
    setIsLoading(true)
    setSessionError(null)
    try {
      await registerRequest(email, password, confirmPassword)
      const response = await currentUser()
      setUser(response.user)
      return response.user
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setUser(null)
      else setSessionError('Your session could not be refreshed. Please try again.')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const signOut = async () => {
    setIsLoading(true)
    try {
      await logoutRequest()
      setUser(null)
      setSessionError(null)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, sessionError, login, register, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

// Context and provider intentionally share this focused module.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider')
  return value
}
