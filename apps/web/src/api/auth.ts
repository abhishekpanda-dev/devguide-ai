import { request } from './client'

export interface AuthUser {
  id: string
  email: string
  created_at: string
}

export interface AuthResponse {
  user: AuthUser
}

export const currentUser = () => request<AuthResponse>('/auth/me')
export const login = (email: string, password: string) =>
  request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
export const register = (email: string, password: string, confirmPassword: string) =>
  request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, confirm_password: confirmPassword }),
  })
export const logout = () => request<void>('/auth/logout', { method: 'POST' })
