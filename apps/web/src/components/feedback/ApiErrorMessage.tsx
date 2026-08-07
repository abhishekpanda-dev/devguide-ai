import { ApiError } from '../../api/client'

export function ApiErrorMessage({
  error,
  fallback = 'Something went wrong.',
}: {
  error: unknown
  fallback?: string
}) {
  const apiError = error instanceof ApiError ? error : null
  return (
    <div className="notice noticeError" role="alert">
      <strong>{apiError?.message ?? fallback}</strong>
      {apiError?.correlationId && (
        <span>
          Reference: <code>{apiError.correlationId}</code>
        </span>
      )}
    </div>
  )
}
