import { Link } from 'react-router'
import type {
  Analysis,
  AnalysisSummary,
  CodeFindingsResponse,
  Repository,
  StructureResponse,
} from '../../api/types'
import { ApiErrorMessage } from '../feedback/ApiErrorMessage'
import { DependencyVisualization } from './DependencyVisualization'

export function DashboardWorkspace({
  repository,
  analysis,
  summary,
  structure,
  findings,
  summaryError,
  structureError,
}: {
  repository: Repository
  analysis: Analysis
  summary?: AnalysisSummary
  structure?: StructureResponse
  findings?: CodeFindingsResponse
  summaryError?: unknown
  structureError?: unknown
}) {
  return (
    <main className="dashboardWorkspace" aria-label="Repository intelligence workspace">
      <div className="workspaceHeading">
        <div>
          <p className="eyebrow">Repository intelligence</p>
          <h1>{repository.name}</h1>
          <p>
            {repository.owner} · {analysis.current_stage ?? 'awaiting analysis stage'}
          </p>
        </div>
        <a
          className="sourceLink"
          href={repository.normalized_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          View source
        </a>
      </div>
      <section className="workspaceHero">
        <div>
          <p className="panelLabel">Analysis state</p>
          <h2>
            {analysis.status === 'completed'
              ? 'Repository evidence is ready'
              : `Analysis ${analysis.status}`}
          </h2>
          <p>
            {summary
              ? `${summary.files_analyzed} persisted files · ${summary.chunks_created} evidence chunks · ${summary.total_lines} lines`
              : 'Persisted parser summary is unavailable.'}
          </p>
        </div>
        <div className="workspaceProgress">
          <span>{analysis.progress_percent}%</span>
          <progress value={analysis.progress_percent} max="100" />
        </div>
      </section>
      {Boolean(summaryError) && (
        <ApiErrorMessage error={summaryError} fallback="Repository summary is unavailable." />
      )}
      <div className="workspaceColumns">
        <section className="dashboardCard">
          <div className="cardHeading">
            <h2>Probable entry points</h2>
            <Link to={`/analyses/${analysis.id}/structure`}>Open structure</Link>
          </div>
          {structureError ? (
            <ApiErrorMessage error={structureError} fallback="Entry points are unavailable." />
          ) : structure?.entry_points.length ? (
            <ul className="codeList">
              {structure.entry_points.slice(0, 6).map((file) => (
                <li key={file.path}>
                  <code>{file.path}</code>
                  <span>
                    {file.entry_point_reason ?? 'Heuristic entry point'} ·{' '}
                    {Math.round(file.entry_point_confidence * 100)}%
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="emptyCompact">No probable entry points were identified.</p>
          )}
        </section>
        <section className="dashboardCard">
          <div className="cardHeading">
            <h2>Most connected files</h2>
            <Link to={`/analyses/${analysis.id}/structure`}>Inspect edges</Link>
          </div>
          {structure?.summary.most_connected_files.length ? (
            <ul className="codeList">
              {structure.summary.most_connected_files.slice(0, 6).map((file) => (
                <li key={file.path}>
                  <code>{file.path}</code>
                  <span>
                    {file.inbound_dependency_count} inbound · {file.outbound_dependency_count}{' '}
                    outbound
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="emptyCompact">No connected-file evidence is available.</p>
          )}
        </section>
      </div>
      <DependencyVisualization
        analysis={analysis}
        structure={structure}
        findings={findings}
        error={structureError}
      />
      <section className="dashboardCard">
        <div className="cardHeading">
          <h2>Primary findings</h2>
          <Link to={`/analyses/${analysis.id}/findings`}>View all</Link>
        </div>
        {findings?.findings.length ? (
          <ul className="findingRows">
            {findings.findings.slice(0, 4).map((item) => (
              <li key={item.id}>
                <span className={`severityMark severity-${item.severity}`}>
                  {item.severity[0].toUpperCase()}
                </span>
                <div>
                  <strong>{item.title}</strong>
                  <a href={item.source_url} target="_blank" rel="noopener noreferrer">
                    {item.path}:{item.start_line}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="emptyCompact">No persisted findings to display.</p>
        )}
      </section>
    </main>
  )
}
