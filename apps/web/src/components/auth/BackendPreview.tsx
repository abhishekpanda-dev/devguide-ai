export function BackendPreview({
  emailReady,
  passwordReady,
}: {
  emailReady: boolean
  passwordReady: boolean
}) {
  return (
    <section
      className="authPreviewPanel backendPreview"
      aria-label="Interactive authentication request preview"
    >
      <header className="authPreviewHeader">
        <span>LIVE CODE PREVIEW</span>
        <span>Interactive authentication preview</span>
      </header>
      <pre aria-live="polite">{`from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="DevGuide AI")

class LoginRequest(BaseModel):
    email: str
    password: str

email_received = ${emailReady ? 'True' : 'False'}
password_received = ${passwordReady ? 'True' : 'False'}${emailReady && passwordReady ? '\nrequest_ready = True' : ''}`}</pre>
      <p className="previewDisclaimer">
        Decorative browser-generated preview. No credentials or server output are displayed.
      </p>
    </section>
  )
}
