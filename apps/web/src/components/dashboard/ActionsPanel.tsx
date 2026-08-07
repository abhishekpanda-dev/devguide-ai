import { useState } from 'react'
import { Link } from 'react-router'
import type {
  Analysis,
  CodeFindingsResponse,
  QualityResponse,
  StructureResponse,
} from '../../api/types'
import { ApiErrorMessage } from '../feedback/ApiErrorMessage'

type Tab = 'findings' | 'quality' | 'actions'
export function ActionsPanel({
  analysis,
  findings,
  quality,
  structure,
  findingsError,
  qualityError,
}: {
  analysis: Analysis
  findings?: CodeFindingsResponse
  quality?: QualityResponse
  structure?: StructureResponse
  findingsError?: unknown
  qualityError?: unknown
}) {
  const [tab, setTab] = useState<Tab>('findings')
  return (
    <aside className="actionsPanel" aria-label="Findings and actions">
      <div className="panelTabs" role="tablist" aria-label="Dashboard details">
        {(['findings', 'quality', 'actions'] as const).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={tab === item}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="panelScroll">
        {tab === 'findings' &&
          (findingsError ? (
            <ApiErrorMessage error={findingsError} fallback="Findings are unavailable." />
          ) : (
            <>
              <p className="panelIntro">Top persisted static findings</p>
              {findings?.findings.slice(0, 5).map((item) => (
                <article className="actionCard" key={item.id}>
                  <div>
                    <span className={`severityBadge severityBadge-${item.severity}`}>
                      {item.severity}
                    </span>
                    <strong>{item.title}</strong>
                  </div>
                  <p>{item.explanation}</p>
                  <a
                    className="sourcePath"
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {item.path}:{item.start_line}
                  </a>
                  <Link to={`/analyses/${analysis.id}/findings`}>
                    Review and generate probable fix
                  </Link>
                </article>
              ))}
              {!findings?.findings.length && <p className="emptyCompact">No persisted findings.</p>}
              <Link className="panelFooterLink" to={`/analyses/${analysis.id}/findings`}>
                View all findings
              </Link>
            </>
          ))}
        {tab === 'quality' &&
          (qualityError ? (
            <ApiErrorMessage error={qualityError} fallback="Quality intelligence is unavailable." />
          ) : (
            <>
              <p className="panelIntro">
                Score {quality?.overall_score ?? '—'}/100 ·{' '}
                {quality?.score_version ?? 'unavailable'}
              </p>
              {quality?.score_breakdown.slice(0, 4).map((item) => (
                <article className="actionCard" key={`${item.category}-${item.signal_type}`}>
                  <strong>{item.points_deducted} point deduction</strong>
                  <p>{item.explanation}</p>
                </article>
              ))}
              {quality?.unused_code_candidates.slice(0, 2).map((item) => (
                <article className="actionCard" key={item.id}>
                  <strong>Unused-code candidate: {item.symbol_name}</strong>
                  <a
                    className="sourcePath"
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {item.path}:{item.start_line}
                  </a>
                </article>
              ))}
              {quality?.duplicate_code_groups.slice(0, 1).map((group) => (
                <article className="actionCard" key={group.group_id}>
                  <strong>Duplicate-code review lead</strong>
                  <p>
                    {group.members.length} matching regions · {group.match_type}
                  </p>
                  <Link to={`/analyses/${analysis.id}/quality`}>Compare candidates</Link>
                </article>
              ))}
              {quality?.limitations.slice(0, 2).map((limitation) => (
                <article className="actionCard actionCard-muted" key={limitation}>
                  <span className="eyebrow">Quality limitation</span>
                  <p>{limitation}</p>
                </article>
              ))}
              {!quality?.score_breakdown.length && !quality?.unused_code_candidates.length && (
                <p className="emptyCompact">No bounded quality actions.</p>
              )}
              <Link className="panelFooterLink" to={`/analyses/${analysis.id}/quality`}>
                View full quality report
              </Link>
            </>
          ))}
        {tab === 'actions' && (
          <>
            <p className="panelIntro">Prioritized from persisted signals</p>
            {findings?.findings.find((item) => item.severity === 'high') && (
              <Link className="actionPrompt" to={`/analyses/${analysis.id}/findings`}>
                Review high-severity finding
              </Link>
            )}
            {quality?.unused_code_candidates.length ? (
              <Link className="actionPrompt" to={`/analyses/${analysis.id}/quality`}>
                Review unused-code candidates
              </Link>
            ) : null}
            {quality?.duplicate_code_groups.length ? (
              <Link className="actionPrompt" to={`/analyses/${analysis.id}/quality`}>
                Inspect duplicate-code groups
              </Link>
            ) : null}
            {structure?.summary.highest_outbound_files.some(
              (file) => file.outbound_dependency_count >= 10,
            ) ? (
              <Link className="actionPrompt" to={`/analyses/${analysis.id}/structure`}>
                Review high fan-out file
              </Link>
            ) : null}
            <Link className="actionPrompt" to={`/analyses/${analysis.id}/ask`}>
              Ask DevGuide about architecture
            </Link>
          </>
        )}
      </div>
    </aside>
  )
}
