import { NavLink } from 'react-router'
import type {
  Analysis,
  AnalysisSummary,
  CodeFindingsResponse,
  QualityResponse,
  StructureResponse,
} from '../../api/types'

export function RepositorySidebar({
  analysis,
  summary,
  findings,
  structure,
  quality,
}: {
  analysis: Analysis
  summary?: AnalysisSummary
  findings?: CodeFindingsResponse
  structure?: StructureResponse
  quality?: QualityResponse
}) {
  const languages =
    structure?.summary?.language_counts ??
    Object.fromEntries(summary?.languages.map((item) => [item.language, item.file_count]) ?? [])
  const maxLanguage = Math.max(1, ...Object.values(languages))
  const nav = [
    { label: 'Overview', to: `/repositories/${analysis.repository_id}` },
    { label: 'Ask DevGuide', to: `/analyses/${analysis.id}/ask` },
    { label: 'Findings', to: `/analyses/${analysis.id}/findings` },
    { label: 'Structure', to: `/analyses/${analysis.id}/structure` },
    { label: 'Quality', to: `/analyses/${analysis.id}/quality` },
    { label: 'Analysis progress', to: `/analyses/${analysis.id}` },
  ]
  return (
    <aside className="repositorySidebar" aria-label="Repository summary">
      <section>
        <p className="panelLabel">Health score</p>
        <div className="sidebarScore">
          {quality?.overall_score ?? '—'}
          <span>/100</span>
        </div>
        <small>{quality?.score_version ?? 'Quality data unavailable'}</small>
      </section>
      <section>
        <p className="panelLabel">Repository metrics</p>
        <dl className="dashboardMetricGrid">
          <div>
            <dt>Files</dt>
            <dd>{structure?.summary.file_count ?? summary?.files_analyzed ?? '—'}</dd>
          </div>
          <div>
            <dt>Edges</dt>
            <dd>{structure?.summary.edge_count ?? '—'}</dd>
          </div>
          <div>
            <dt>Languages</dt>
            <dd>{Object.keys(languages).length || '—'}</dd>
          </div>
          <div>
            <dt>Findings</dt>
            <dd>{findings?.total_count ?? '—'}</dd>
          </div>
          <div>
            <dt>Unused</dt>
            <dd>{quality?.summary.unused_candidate_count ?? '—'}</dd>
          </div>
          <div>
            <dt>Duplicates</dt>
            <dd>{quality?.summary.duplicate_group_count ?? '—'}</dd>
          </div>
        </dl>
      </section>
      <section aria-labelledby="sidebar-findings-heading">
        <p className="panelLabel" id="sidebar-findings-heading">
          Finding summary
        </p>
        <ul className="severitySummary">
          <li>
            <span className="severityMark severity-high">H</span>High{' '}
            <strong>{findings?.severity_counts.high ?? 0}</strong>
          </li>
          <li>
            <span className="severityMark severity-warning">W</span>Warning{' '}
            <strong>{findings?.severity_counts.warning ?? 0}</strong>
          </li>
          <li>
            <span className="severityMark severity-info">I</span>Info{' '}
            <strong>{findings?.severity_counts.info ?? 0}</strong>
          </li>
        </ul>
      </section>
      <section aria-labelledby="sidebar-languages-heading">
        <p className="panelLabel" id="sidebar-languages-heading">
          Languages
        </p>
        {Object.keys(languages).length ? (
          <ul className="languageBars">
            {Object.entries(languages)
              .slice(0, 6)
              .map(([name, count]) => (
                <li key={name} aria-label={`${name}: ${count} files`}>
                  <div className="languageRow">
                    <span className="languageName" title={name}>
                      {name}
                    </span>
                    <span className="languageCount">
                      <strong>{count}</strong> files
                    </span>
                  </div>
                  <span className="languageTrack">
                    <span style={{ width: `${Math.max(8, (count / maxLanguage) * 100)}%` }} />
                  </span>
                </li>
              ))}
          </ul>
        ) : (
          <p className="mutedCompact">No language data.</p>
        )}
      </section>
      <nav className="sidebarNav" aria-label="Analysis navigation">
        {nav.map((item) => (
          <NavLink key={item.label} to={item.to} end={item.label === 'Overview'}>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
