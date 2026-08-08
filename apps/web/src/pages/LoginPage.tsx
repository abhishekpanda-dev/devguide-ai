import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { getSafeReturnPath } from '../auth/returnPath'
import { AuthLayout } from '../components/auth/AuthLayout'
import { PasswordField } from '../components/auth/PasswordField'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [authError, setAuthError] = useState<ApiError | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setAuthError(null)
    const next: Record<string, string> = {}
    if (!/^\S+@\S+\.\S+$/.test(email)) next.email = 'Enter a valid email address.'
    if (!password) next.password = 'Enter your password.'
    setErrors(next)
    if (Object.keys(next).length) return

    setIsSubmitting(true)
    try {
      await login(email, password)
      setIsSuccess(true)
      setPassword('')
      navigate(getSafeReturnPath(location.state), { replace: true })
    } catch (error) {
      setAuthError(error instanceof ApiError ? error : new ApiError('Sign in failed.', 'unknown'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout
      emailReady={Boolean(email)}
      passwordReady={Boolean(password)}
      previewState={
        isSubmitting ? 'submitting' : isSuccess ? 'success' : authError ? 'failure' : 'idle'
      }
    >
      <form className="authCard" onSubmit={handleSubmit} noValidate>
        <p className="eyebrow">Secure workspace access</p>
        <h2>Welcome back</h2>
        <p>Sign in to continue to your workspace</p>
        {authError && (
          <div className="authError" role="alert">
            Email or password is incorrect.
            {authError.correlationId && <small> Reference: {authError.correlationId}</small>}
          </div>
        )}
        <div className="authField">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'email-error' : undefined}
          />
          {errors.email && (
            <span id="email-error" className="fieldError">
              {errors.email}
            </span>
          )}
        </div>
        <PasswordField
          id="password"
          label="Password"
          value={password}
          onChange={setPassword}
          error={errors.password}
        />
        <button className="authSubmit" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="authSwitch">
          Don’t have an account? <Link to="/register">Sign up</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
