import { Link } from 'react-router'
import type { Analysis, Repository } from '../../api/types'

export function DashboardToolbar({
  repository,
  analysis,
  onRefresh,
}: {
  repository: Repository
  analysis: Analysis
  onRefresh: () => void
}) {
  const sha = repository.latest_commit_sha?.slice(0, 8) ?? 'pending'
  return (
    <header className="dashboardToolbar">
      <div className="dashboardRepoIdentity">
        <span className="dashboardMark" aria-hidden="true">
          DG
        </span>
        <div>
          <strong>
            {repository.owner}/{repository.name}
          </strong>
          <span>
            {repository.default_branch ?? 'default branch'} · <code>{sha}</code>
          </span>
        </div>
      </div>
      <div className="toolbarStatus" role="status">
        <span className={`statusDot statusDot-${analysis.status}`} />
        {analysis.status} · {analysis.progress_percent}%
      </div>
      <nav className="dashboardToolbarNav" aria-label="Repository tools">
        <Link to="/">Analyze</Link>
        <button type="button" className="toolButton" onClick={onRefresh}>
          Refresh
        </button>
        <Link to={`/analyses/${analysis.id}/ask`}>Ask</Link>
        <Link to={`/analyses/${analysis.id}/findings`}>Findings</Link>
        <Link to={`/analyses/${analysis.id}/structure`}>Structure</Link>
        <Link to={`/analyses/${analysis.id}/quality`}>Quality</Link>
      </nav>
    </header>
  )
}
