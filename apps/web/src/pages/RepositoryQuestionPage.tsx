import { FormEvent, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router'
import { askQuestion } from '../api/questions'
import type { QuestionRequest } from '../api/types'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'
import { CitationList } from '../components/questions/CitationList'
import { FeatureLocationAnswer } from '../components/questions/FeatureLocationAnswer'

export function RepositoryQuestionPage() {
  const { analysisId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const [question, setQuestion] = useState(() =>
    searchParams.get('path')
      ? `What would be affected if I change ${searchParams.get('path')}?`
      : '',
  )
  const [error, setError] = useState<string | null>(null)
  const [languages, setLanguages] = useState('')
  const [pathPrefix, setPathPrefix] = useState('')
  const [limit, setLimit] = useState(10)
  const [score, setScore] = useState(1)
  const [citations, setCitations] = useState(10)
  const mutation = useMutation({
    mutationFn: (body: QuestionRequest) => askQuestion(analysisId, body),
  })
  function submit(event: FormEvent) {
    event.preventDefault()
    const normalized = question.trim()
    if (!normalized) {
      setError('Enter a question about this repository.')
      return
    }
    setError(null)
    mutation.mutate({
      question: normalized,
      language_filters: languages
        .split(',')
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean),
      path_prefix: pathPrefix.trim() || undefined,
      retrieval_limit: limit,
      retrieval_minimum_score: score,
      maximum_citations: citations,
    })
  }
  const answer = mutation.data
  return (
    <div className="narrow">
      <p className="eyebrow">Evidence-backed Q&amp;A</p>
      <h1>Ask DevGuide</h1>
      <p className="lede">
        Answers are limited to evidence retrieved from analysis <code>{analysisId}</code>.
      </p>
      <form className="panel formPanel questionForm" onSubmit={submit} noValidate>
        <label htmlFor="question">Question</label>
        <textarea
          id="question"
          rows={4}
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value)
            setError(null)
          }}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? 'question-error' : 'question-help'}
          autoFocus
        />
        <p id="question-help" className="help">
          Ask about files, symbols, configuration, or behavior evidenced in the repository.
        </p>
        {error && (
          <p id="question-error" className="fieldError" role="alert">
            {error}
          </p>
        )}
        <details>
          <summary>Advanced retrieval controls</summary>
          <div className="controlGrid">
            <label>
              Language filters <span>Comma-separated</span>
              <input
                value={languages}
                onChange={(event) => setLanguages(event.target.value)}
                placeholder="python, typescript"
              />
            </label>
            <label>
              Path prefix <span>Repository-relative</span>
              <input
                value={pathPrefix}
                onChange={(event) => setPathPrefix(event.target.value)}
                placeholder="apps/api"
              />
            </label>
            <label>
              Retrieval limit
              <input
                type="number"
                min="1"
                max="100"
                value={limit}
                onChange={(event) => setLimit(event.target.valueAsNumber)}
              />
            </label>
            <label>
              Minimum score
              <input
                type="number"
                min="0"
                max="110"
                step="0.1"
                value={score}
                onChange={(event) => setScore(event.target.valueAsNumber)}
              />
            </label>
            <label>
              Maximum citations
              <input
                type="number"
                min="1"
                max="100"
                value={citations}
                onChange={(event) => setCitations(event.target.valueAsNumber)}
              />
            </label>
          </div>
        </details>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Analyzing repository evidence…' : 'Ask DevGuide'}
        </button>
        {mutation.isError && <ApiErrorMessage error={mutation.error} />}
      </form>
      <div aria-live="polite">
        {answer && (
          <article className="answer">
            <div className="panelHeader">
              <div>
                <p className="eyebrow">Answer</p>
                <h2>
                  {answer.insufficient_evidence
                    ? 'Insufficient evidence'
                    : 'Evidence-backed response'}
                </h2>
              </div>
              <span className="quality">{answer.evidence_quality} evidence</span>
            </div>
            <p className="answerText">
              {answer.answer ||
                'DevGuide could not find enough relevant repository evidence to answer this question.'}
            </p>
            {answer.feature_location && (
              <FeatureLocationAnswer analysisId={analysisId} result={answer.feature_location} />
            )}
            <CitationList citations={answer.citations} />
            {answer.limitations.length > 0 && (
              <section className="limitations">
                <h3>Limitations</h3>
                <ul>
                  {answer.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            )}
            <footer className="answerMeta">
              {answer.provider && (
                <span>
                  Provider: <code>{answer.provider}</code>
                </span>
              )}
              {answer.model && (
                <span>
                  Model: <code>{answer.model}</code>
                </span>
              )}
              {answer.correlation_id && (
                <span>
                  Reference: <code>{answer.correlation_id}</code>
                </span>
              )}
            </footer>
          </article>
        )}
      </div>
      <p className="backLink">
        <Link to={`/analyses/${analysisId}`}>← Back to analysis</Link>
      </p>
    </div>
  )
}
