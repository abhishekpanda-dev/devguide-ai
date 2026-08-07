import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { getAnalysisSummary } from '../api/analyses'
import { getRepository, getRepositoryAnalyses } from '../api/repositories'
import { AnalysisSummary } from '../components/analysis/AnalysisSummary'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'
import { RepositoryFacts } from '../components/repository/RepositoryFacts'

export function RepositoryDashboardPage() {
  const { repositoryId = '' } = useParams()
  const repository = useQuery({
    queryKey: ['repository', repositoryId],
    queryFn: () => getRepository(repositoryId),
  })
  const analyses = useQuery({
    queryKey: ['repository-analyses', repositoryId],
    queryFn: () => getRepositoryAnalyses(repositoryId),
  })
  const latest = analyses.data?.items[0]
  const summary = useQuery({
    queryKey: ['analysis-summary', latest?.id],
    queryFn: () => getAnalysisSummary(latest?.id ?? ''),
    enabled: Boolean(latest?.id),
  })
  if (repository.isPending || analyses.isPending)
    return (
      <div className="state" role="status">
        Loading repository…
      </div>
    )
  if (repository.isError)
    return (
      <div className="narrow">
        <h1>Repository unavailable</h1>
        <ApiErrorMessage error={repository.error} />
      </div>
    )
  if (analyses.isError)
    return (
      <div className="narrow">
        <h1>{repository.data.name}</h1>
        <ApiErrorMessage error={analyses.error} fallback="Analysis history could not be loaded." />
      </div>
    )
  return (
    <div>
      <div className="pageHeading">
        <div>
          <p className="eyebrow">{repository.data.owner}</p>
          <h1>{repository.data.name}</h1>
          <p className="lede">Observed repository metadata and available analysis state.</p>
        </div>
        {latest && (
          <div className="actions">
            <Link className="button" to={`/analyses/${latest.id}/ask`}>
              Ask DevGuide
            </Link>
            <Link className="button secondary" to={`/analyses/${latest.id}/findings`}>
              View code findings
            </Link>
            <Link className="button secondary" to={`/analyses/${latest.id}/structure`}>
              View structure
            </Link>
          </div>
        )}
      </div>
      <section className="panel">
        <h2>Repository details</h2>
        <RepositoryFacts repository={repository.data} />
      </section>
      <div className="sectionHeading">
        <h2>Latest analysis</h2>
        {latest && <Link to={`/analyses/${latest.id}`}>View progress</Link>}
      </div>
      {latest ? (
        <AnalysisSummary analysis={latest} />
      ) : (
        <div className="emptyState">
          <h3>No analyses available</h3>
          <p>No analysis records were returned for this repository.</p>
        </div>
      )}
      {latest && (
        <section className="panel" aria-labelledby="statistics-heading">
          <h2 id="statistics-heading">Persisted analysis statistics</h2>
          {summary.isPending ? (
            <div className="state" role="status">
              Loading analysis statistics…
            </div>
          ) : summary.isError ? (
            <ApiErrorMessage
              error={summary.error}
              fallback="Analysis statistics could not be loaded."
            />
          ) : (
            <>
              {summary.data.files_analyzed === 0 && (
                <div className="emptyState">
                  <h3>No analyzed files</h3>
                  <p>The parser completed without persisting any supported files.</p>
                </div>
              )}
              <dl className="statisticsGrid">
                <div>
                  <dt>Files analyzed</dt>
                  <dd>{summary.data.files_analyzed}</dd>
                </div>
                <div>
                  <dt>Evidence chunks</dt>
                  <dd>{summary.data.chunks_created}</dd>
                </div>
                <div>
                  <dt>Total lines</dt>
                  <dd>{summary.data.total_lines}</dd>
                </div>
                <div>
                  <dt>Test files</dt>
                  <dd>{summary.data.test_file_count}</dd>
                </div>
                <div>
                  <dt>Documentation files</dt>
                  <dd>{summary.data.documentation_file_count}</dd>
                </div>
                <div>
                  <dt>Skipped files</dt>
                  <dd>{summary.data.skipped_file_count}</dd>
                </div>
              </dl>
              <div className="languageSummary">
                <h3>Detected languages</h3>
                {summary.data.languages.length > 0 ? (
                  <ul>
                    {summary.data.languages.map((item) => (
                      <li key={item.language}>
                        <strong>{item.language}</strong>
                        <span>
                          {item.file_count} {item.file_count === 1 ? 'file' : 'files'} ·{' '}
                          {item.line_count} lines
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No supported languages were detected.</p>
                )}
              </div>
              {summary.data.limitations.length > 0 && (
                <aside className="limitations">
                  <h3>Parser limitations</h3>
                  <ul>
                    {summary.data.limitations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </aside>
              )}
            </>
          )}
        </section>
      )}
    </div>
  )
}
