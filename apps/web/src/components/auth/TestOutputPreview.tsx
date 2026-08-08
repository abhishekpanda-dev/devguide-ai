export type AuthenticationPreviewState = 'idle' | 'submitting' | 'success' | 'failure'

export function TestOutputPreview({
  emailReady,
  passwordReady,
  state,
}: {
  emailReady: boolean
  passwordReady: boolean
  state: AuthenticationPreviewState
}) {
  const ready = emailReady && passwordReady
  return (
    <section
      className="authPreviewPanel testOutputPreview"
      aria-label="Authentication status preview"
    >
      <header className="authPreviewHeader">
        <span>TEST OUTPUT</span>
        <span>Safe local state</span>
      </header>
      <div className="testOutputBody" aria-live="polite">
        <p data-state={emailReady ? 'received' : 'waiting'}>
          <span aria-hidden="true">{emailReady ? '✓' : '○'}</span> Email field{' '}
          {emailReady ? 'received' : 'waiting'}
        </p>
        <p data-state={passwordReady ? 'received' : 'waiting'}>
          <span aria-hidden="true">{passwordReady ? '✓' : '○'}</span> Password field{' '}
          {passwordReady ? 'received' : 'waiting'}
        </p>
        {state === 'submitting' && <p data-state="active">◉ Authenticating</p>}
        {state === 'success' && (
          <>
            <p data-state="received">✓ Authentication accepted</p>
            <p data-state="received">✓ Session established</p>
            <p data-state="received">✓ User profile loaded</p>
          </>
        )}
        {state === 'failure' && (
          <>
            <p data-state="rejected">✕ Authentication rejected</p>
            <p data-state="waiting">○ Session not established</p>
          </>
        )}
        {state === 'idle' && (
          <p data-state={ready ? 'received' : 'waiting'}>
            <span aria-hidden="true">{ready ? '✓' : '○'}</span> Request{' '}
            {ready ? 'ready' : 'not ready'}
          </p>
        )}
      </div>
      <p className="previewDisclaimer">Interface state only — not automated test output.</p>
    </section>
  )
}
