import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { getRepositoryQuality } from '../api/analyses'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'

export function RepositoryQualityPage() {
  const { analysisId = '' } = useParams()
  const query = useQuery({ queryKey: ['repository-quality', analysisId], queryFn: () => getRepositoryQuality(analysisId), enabled: Boolean(analysisId) })
  if (query.isPending) return <div className="state" role="status">Loading repository qualityâ€¦</div>
  if (query.isError) return <ApiErrorMessage error={query.error} fallback="Repository quality could not be loaded." />
  const data = query.data
  return <div>
    <p className="eyebrow">Deterministic static signals</p>
    <h1>Repository Quality</h1>
    <p className="lede">Candidates and score signals are explainable static-analysis results, not confirmed bugs or industry benchmarks.</p>
    <section className="panel" aria-labelledby="health-score"><h2 id="health-score">Health score</h2><p className="healthScore">{data.overall_score}<span>/100</span></p><p>Formula {data.score_version}</p><dl className="statisticsGrid">{Object.entries(data.category_scores).map(([name, score]) => <div key={name}><dt>{name}</dt><dd>{score}</dd></div>)}</dl></section>
    <section className="panel"><h2>Explainable deductions</h2>{data.score_breakdown.length ? <ul>{data.score_breakdown.map(item => <li key={`${item.category}-${item.signal_type}`}><strong>{item.points_deducted} points â€” {item.signal_type}</strong> ({item.count} signals): {item.explanation}</li>)}</ul> : <div className="emptyState"><h3>No deductions</h3><p>No configured deterministic deduction signals were persisted.</p></div>}</section>
    <section className="panel"><h2>Unused-code candidates</h2>{data.unused_code_candidates.length ? data.unused_code_candidates.map(item => <article className="findingCard" key={item.id}><h3>Candidate: <code>{item.symbol_name}</code></h3><p><a href={item.source_url} target="_blank" rel="noopener noreferrer">{item.path}:{item.start_line}-{item.end_line}</a> Â· {Math.round(item.confidence * 100)}% confidence</p><p>{item.reason}</p><p className="findingRecommendation"><strong>Recommendation:</strong> {item.recommendation}</p></article>) : <div className="emptyState"><h3>No unused-code candidates</h3><p>No high-confidence candidates matched the bounded policy.</p></div>}</section>
    <section className="panel"><h2>Duplicate-code candidates</h2>{data.duplicate_code_groups.length ? data.duplicate_code_groups.map(group => <article key={group.group_id}><h3>Candidate group {group.group_id}</h3><p>Exact normalized match Â· {Math.round(group.confidence * 100)}% confidence</p><ul>{group.members.map(member => <li key={`${member.path}-${member.start_line}`}><a href={member.source_url} target="_blank" rel="noopener noreferrer">{member.path}:{member.start_line}-{member.end_line}</a></li>)}</ul><p>{group.recommendation}</p></article>) : <div className="emptyState"><h3>No duplicate-code candidates</h3><p>No sufficiently large exact normalized duplicate groups were detected.</p></div>}</section>
    {data.limitations.length ? <aside className="limitations"><h2>Limitations</h2><ul>{data.limitations.map(item => <li key={item}>{item}</li>)}</ul></aside> : null}
    <p className="backLink"><Link to={`/analyses/${analysisId}`}>Back to analysis</Link></p>
  </div>
}
