interface ErrorEnvelope {
  error?: { code?: string; message?: string; correlation_id?: string }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly correlationId?: string,
    public readonly status?: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(
      'Unable to reach DevGuide AI. Check your connection and try again.',
      'network_error',
    )
  }
  if (!response.ok) {
    let body: ErrorEnvelope = {}
    try {
      body = (await response.json()) as ErrorEnvelope
    } catch {
      /* malformed errors stay private */
    }
    const correlationId =
      body.error?.correlation_id ?? response.headers.get('x-correlation-id') ?? undefined
    throw new ApiError(
      body.error?.message ?? 'The request could not be completed.',
      body.error?.code ?? 'request_failed',
      correlationId,
      response.status,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
