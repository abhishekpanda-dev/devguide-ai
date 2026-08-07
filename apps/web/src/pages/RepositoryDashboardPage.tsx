import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
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
  const latest = analyses.data.items[0]
  return (
    <div>
      <div className="pageHeading">
        <div>
          <p className="eyebrow">{repository.data.owner}</p>
          <h1>{repository.data.name}</h1>
          <p className="lede">Observed repository metadata and available analysis state.</p>
        </div>
        {latest && (
          <Link className="button" to={`/analyses/${latest.id}/ask`}>
            Ask DevGuide
          </Link>
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
      <aside className="notice">
        <strong>Analysis limitations</strong>
        <p>
          The current API does not expose architecture summaries, language statistics, health
          scores, or file counts. This dashboard does not infer them.
        </p>
      </aside>
    </div>
  )
}
