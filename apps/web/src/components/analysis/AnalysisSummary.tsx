import type { Analysis } from '../../api/types'
import { StatusBadge } from '../feedback/StatusBadge'

export function AnalysisSummary({
  analysis,
  showProgress = false,
}: {
  analysis: Analysis
  showProgress?: boolean
}) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Analysis</p>
          <h2>{analysis.current_stage?.replaceAll('_', ' ') ?? 'Waiting to start'}</h2>
        </div>
        <StatusBadge status={analysis.status} />
      </div>
      {showProgress && (
        <>
          <div className="progressLabels">
            <span>Progress</span>
            <strong>{analysis.progress_percent}%</strong>
          </div>
          <progress max="100" value={analysis.progress_percent}>
            {analysis.progress_percent}%
          </progress>
        </>
      )}
      <dl className="metaRow">
        <div>
          <dt>Analysis ID</dt>
          <dd>
            <code>{analysis.id}</code>
          </dd>
        </div>
        <div>
          <dt>Pipeline</dt>
          <dd>
            <code>{analysis.pipeline_version}</code>
          </dd>
        </div>
      </dl>
      {analysis.error_message && (
        <div className="notice noticeError" role="alert">
          {analysis.error_message}
        </div>
      )}
    </section>
  )
}
