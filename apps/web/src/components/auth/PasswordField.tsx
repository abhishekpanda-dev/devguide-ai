import { useState } from 'react'

export function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete = 'current-password',
  error,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  autoComplete?: string
  error?: string
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="authField">
      <label htmlFor={id}>{label}</label>
      <div className="passwordInput">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          placeholder="Enter your password"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? 'Hide password' : 'Show password'}
        >
          {visible ? 'Hide' : 'Show'}
        </button>
      </div>
      {error && (
        <span id={`${id}-error`} className="fieldError">
          {error}
        </span>
      )}
    </div>
  )
}
