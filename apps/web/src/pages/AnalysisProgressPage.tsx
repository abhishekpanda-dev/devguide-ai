import { useQuery } from '@tanstack/react-query'
import { Link, Navigate, useLocation, useParams } from 'react-router'
import { getAnalysis } from '../api/analyses'
import { AnalysisSummary } from '../components/analysis/AnalysisSummary'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'
import { dashboardFocusTarget } from './analysisNavigation'

const terminal = new Set(['partial', 'completed', 'failed', 'cancelled'])

export function AnalysisProgressPage() {
  const { analysisId = '' } = useParams()
  const location = useLocation()
  const submittedRepositoryId = (location.state as { repositoryId?: string } | null)?.repositoryId
  const query = useQuery({
    queryKey: ['analysis', analysisId],
    queryFn: () => getAnalysis(analysisId),
    enabled: Boolean(analysisId),
    refetchInterval: (current) =>
      current.state.data && terminal.has(current.state.data.status) ? false : 2000,
  })
  if (query.isPending)
    return (
      <div className="state" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        Loading analysis status…
      </div>
    )
  if (query.isError)
    return (
      <div className="narrow">
        <h1>Analysis unavailable</h1>
        <ApiErrorMessage error={query.error} />
      </div>
    )
  const analysis = query.data
  const repositoryId = analysis.repository_id || submittedRepositoryId
  const usable = analysis.status === 'completed' || analysis.status === 'partial'
  const focusTarget =
    repositoryId && usable ? dashboardFocusTarget(repositoryId, analysis.id, location.search) : null
  if (focusTarget) return <Navigate to={focusTarget} replace />
  return (
    <div className="narrow">
      <p className="eyebrow">Repository analysis</p>
      <h1>{terminal.has(analysis.status) ? 'Analysis status' : 'Analysis in progress'}</h1>
      <p className="lede" aria-live="polite">
        {analysis.status === 'queued'
          ? 'Your analysis is queued and will begin when a worker is available.'
          : analysis.status === 'running'
            ? 'DevGuide is inspecting eligible repository content.'
            : 'The analysis has reached a terminal state.'}
      </p>
      <AnalysisSummary analysis={analysis} showProgress />
      {usable && (
        <div className="actions">
          <Link className="button" to={`/repositories/${repositoryId}`}>
            Open repository dashboard
          </Link>
          <Link className="button secondary" to={`/analyses/${analysis.id}/ask`}>
            Ask DevGuide
          </Link>
        </div>
      )}
    </div>
  )
}
