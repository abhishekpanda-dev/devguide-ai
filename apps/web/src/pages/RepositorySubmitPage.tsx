import { FormEvent, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { submitRepository } from '../api/repositories'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'
import { validateRepositoryUrl } from './repositoryValidation'

export function RepositorySubmitPage() {
  const [sourceUrl, setSourceUrl] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: submitRepository,
    onSuccess: ({ repository, analysis_job }) =>
      navigate(`/analyses/${analysis_job.id}`, { state: { repositoryId: repository.id } }),
  })
  function submit(event: FormEvent) {
    event.preventDefault()
    const error = validateRepositoryUrl(sourceUrl.trim())
    setValidationError(error)
    if (!error) mutation.mutate(sourceUrl.trim())
  }
  return (
    <div className="narrow submitPage">
      <p className="eyebrow">Repository intelligence</p>
      <h1>Understand any codebase faster.</h1>
      <p className="lede">
        Analyze a public GitHub repository and ask questions backed by evidence from the source
        code.
      </p>
      <form className="panel formPanel" onSubmit={submit} noValidate>
        <label htmlFor="repository-url">Public GitHub repository URL</label>
        <div className="inputAction">
          <input
            id="repository-url"
            name="repository-url"
            type="url"
            placeholder="https://github.com/owner/repository"
            value={sourceUrl}
            onChange={(event) => {
              setSourceUrl(event.target.value)
              setValidationError(null)
            }}
            aria-invalid={Boolean(validationError)}
            aria-describedby={validationError ? 'repository-error' : 'repository-help'}
            autoComplete="url"
            autoFocus
          />
          <button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Submitting…' : 'Analyze repository'}
          </button>
        </div>
        {validationError ? (
          <p id="repository-error" className="fieldError" role="alert">
            {validationError}
          </p>
        ) : (
          <p id="repository-help" className="help">
            Only public github.com repositories are supported.
          </p>
        )}
        {mutation.isError && <ApiErrorMessage error={mutation.error} />}
      </form>
      <ol className="workflow" aria-label="How DevGuide works">
        <li>
          <span>01</span>
          <strong>Submit repository</strong>
        </li>
        <li>
          <span>02</span>
          <strong>Analyze code</strong>
        </li>
        <li>
          <span>03</span>
          <strong>Ask questions</strong>
        </li>
      </ol>
      <aside className="safetyNote">
        <strong>Safe by design</strong>
        <span aria-hidden="true"> · </span>Repository code is analyzed as data and never executed.
      </aside>
    </div>
  )
}
