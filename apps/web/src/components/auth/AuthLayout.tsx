import type { ReactNode } from 'react'
import { AuthLogo } from './AuthLogo'
import { BackendPreview } from './BackendPreview'
import { TestOutputPreview, type AuthenticationPreviewState } from './TestOutputPreview'

export function AuthLayout({
  children,
  emailReady,
  passwordReady,
  previewState,
}: {
  children: ReactNode
  emailReady: boolean
  passwordReady: boolean
  previewState: AuthenticationPreviewState
}) {
  return (
    <main className="authPage">
      <section className="authVisualColumn">
        <header className="authBrandHeader">
          <AuthLogo />
        </header>
        <div className="authPreviewGrid">
          <BackendPreview emailReady={emailReady} passwordReady={passwordReady} />
          <TestOutputPreview
            emailReady={emailReady}
            passwordReady={passwordReady}
            state={previewState}
          />
        </div>
      </section>
      <section className="authFormColumn">{children}</section>
    </main>
  )
}
