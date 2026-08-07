import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { getCodeFindings } from '../api/analyses'
import type { FindingCategory, FindingSeverity } from '../api/types'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'

export function CodeFindingsPage() {
  const { analysisId = '' } = useParams()
  const [severity, setSeverity] = useState<FindingSeverity | ''>('')
  const [category, setCategory] = useState<FindingCategory | ''>('')
  const query = useQuery({
    queryKey: ['code-findings', analysisId, severity, category],
    queryFn: () =>
      getCodeFindings(analysisId, {
        severity: severity || undefined,
        category: category || undefined,
      }),
    enabled: Boolean(analysisId),
  })
  return (
    <div>
      <p className="eyebrow">Deterministic review signals</p>
      <h1>Code Findings</h1>
      <p className="lede">
        Potential issues detected by bounded static inspection. Findings are review signals, not
        confirmed bugs or vulnerabilities.
      </p>
      {query.data && (
        <div className="findingSummary" aria-label="Finding counts">
          {(['high', 'warning', 'info'] as const).map((level) => (
            <div key={level} className={`findingCount finding-${level}`}>
              <span>{level}</span>
              <strong>{query.data.severity_counts[level]}</strong>
            </div>
          ))}
        </div>
      )}
      <div className="findingFilters" aria-label="Finding filters">
        <label htmlFor="severity-filter">
          Severity
          <select
            id="severity-filter"
            value={severity}
            onChange={(e) => setSeverity(e.target.value as FindingSeverity | '')}
          >
            <option value="">All</option>
            <option value="high">High</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </label>
        <label htmlFor="category-filter">
          Category
          <select
            id="category-filter"
            value={category}
            onChange={(e) => setCategory(e.target.value as FindingCategory | '')}
          >
            <option value="">All</option>
            <option value="security">Security</option>
            <option value="reliability">Reliability</option>
            <option value="maintainability">Maintainability</option>
          </select>
        </label>
      </div>
      {query.isPending ? (
        <div className="state" role="status">
          Analyzing repository findings...
        </div>
      ) : query.isError ? (
        <ApiErrorMessage error={query.error} fallback="Code findings could not be loaded." />
      ) : query.data.findings.length === 0 ? (
        <div className="emptyState">
          <h2>No findings</h2>
          <p>No deterministic findings were detected by the current ruleset.</p>
        </div>
      ) : (
        <div className="findingList">
          {query.data.findings.map((f) => (
            <article className={`panel findingCard finding-${f.severity}`} key={f.id}>
              <div className="panelHeader">
                <div>
                  <span className="findingSeverity">{f.severity}</span>
                  <h2>{f.title}</h2>
                </div>
                <span className="status">{f.category}</span>
              </div>
              <p className="findingLocation">
                <code>{f.path}</code> ·{' '}
                {f.start_line === f.end_line
                  ? `Line ${f.start_line}`
                  : `Lines ${f.start_line}-${f.end_line}`}
              </p>
              <pre>
                <code>{f.evidence_excerpt}</code>
              </pre>
              <p>{f.explanation}</p>
              <div className="findingRecommendation">
                <strong>Suggested action</strong>
                <p>{f.deterministic_recommendation}</p>
              </div>
              <p className="quality">Confidence {Math.round(f.confidence * 100)}%</p>
              <a
                className="button secondary"
                href={f.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open on GitHub →
              </a>
            </article>
          ))}
        </div>
      )}
      {query.data?.limitations.length ? (
        <aside className="limitations">
          <h2>Analysis limitations</h2>
          <ul>
            {query.data.limitations.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </aside>
      ) : null}
      <p className="backLink">
        <Link to={`/analyses/${analysisId}`}>Back to analysis</Link>
      </p>
    </div>
  )
}
