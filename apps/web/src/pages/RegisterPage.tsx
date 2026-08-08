import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { AuthLayout } from '../components/auth/AuthLayout'
import { PasswordField } from '../components/auth/PasswordField'

export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const navigate = useNavigate()
  const { register } = useAuth()
  const mutation = useMutation({ mutationFn: () => register(email, password, confirm) })
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!/^\S+@\S+\.\S+$/.test(email)) next.email = 'Enter a valid email address.'
    if (password.length < 12) next.password = 'Use at least 12 characters.'
    if (confirm !== password) next.confirm = 'Passwords must match.'
    setErrors(next)
    if (Object.keys(next).length) return
    try {
      await mutation.mutateAsync()
      setPassword('')
      setConfirm('')
      navigate('/repositories/new', { replace: true })
    } catch {
      /* rendered below */
    }
  }
  const apiError = mutation.error instanceof ApiError ? mutation.error : null
  return (
    <AuthLayout
      emailReady={Boolean(email)}
      passwordReady={Boolean(password)}
      previewState={
        mutation.isPending
          ? 'submitting'
          : mutation.isSuccess
            ? 'success'
            : apiError
              ? 'failure'
              : 'idle'
      }
    >
      <form className="authCard" onSubmit={submit} noValidate>
        <p className="eyebrow">Create your workspace</p>
        <h2>Get started</h2>
        <p>Create an account to continue to DevGuide AI</p>
        {apiError && (
          <div className="authError" role="alert">
            An account could not be created with those details.
            {apiError.correlationId && <small> Reference: {apiError.correlationId}</small>}
          </div>
        )}
        <div className="authField">
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          {errors.email && <span className="fieldError">{errors.email}</span>}
        </div>
        <PasswordField
          id="register-password"
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          error={errors.password}
        />
        <PasswordField
          id="confirm-password"
          label="Confirm password"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
          error={errors.confirm}
        />
        <button className="authSubmit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Creating account…' : 'Create account'}
        </button>
        <p className="authSwitch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
