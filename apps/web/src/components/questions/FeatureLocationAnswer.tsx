import { Link } from 'react-router'
import type { FeatureFile, FeatureLocationResult } from '../../api/types'

function FileList({
  analysisId,
  files,
  heading,
}: {
  analysisId: string
  files: FeatureFile[]
  heading: string
}) {
  if (!files.length) return null
  return (
    <section>
      <h3>{heading}</h3>
      <ul className="featureFileList">
        {files.map((file) => (
          <li key={`${heading}:${file.repository_file_id}`}>
            <div className="featureFileHeader">
              <code>{file.path}</code>
              <span className="roleBadge">
                {file.role}
                {file.role_inferred ? ' (inferred)' : ''}
              </span>
              <span>{Math.round(file.confidence * 100)}% probable</span>
            </div>
            <p>{file.reason}</p>
            <div className="featureActions">
              <a href={file.source_url} target="_blank" rel="noopener noreferrer">
                Open exact source
              </a>
              <Link to={`/analyses/${analysisId}?focus=${encodeURIComponent(file.path)}`}>
                Focus in graph
              </Link>
              <Link to={`/analyses/${analysisId}/ask?path=${encodeURIComponent(file.path)}`}>
                Ask about this file
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function FeatureLocationAnswer({
  analysisId,
  result,
}: {
  analysisId: string
  result: FeatureLocationResult
}) {
  const impact = result.impact_summary
  return (
    <section className="featureLocation" aria-labelledby="feature-location-heading">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Probable feature location</p>
          <h2 id="feature-location-heading">Change-impact plan for “{result.feature_phrase}”</h2>
        </div>
      </div>
      <p className="help">
        This plan uses bounded persisted static evidence. Verify the likely code path before
        changing code.
      </p>
      <FileList analysisId={analysisId} files={result.likely_files} heading="Likely files" />
      <div className="impactColumns">
        <FileList
          analysisId={analysisId}
          files={[...impact.direct_dependencies, ...impact.direct_dependents]}
          heading="Direct static impact"
        />
        <FileList
          analysisId={analysisId}
          files={impact.probable_indirect}
          heading="Probable indirect impact"
        />
      </div>
      <FileList
        analysisId={analysisId}
        files={result.related_tests}
        heading="Likely tests to inspect — coverage not proven"
      />
      <section>
        <h3>Structured change plan</h3>
        <ol className="changePlan">
          <li>
            <strong>Start here:</strong>{' '}
            {result.change_plan.start_here.join(', ') || 'No defensible starting file.'}
          </li>
          <li>
            <strong>Inspect these files:</strong>{' '}
            {result.change_plan.inspect_files.join(', ') || 'None ranked.'}
          </li>
          <li>
            <strong>Likely code path:</strong>{' '}
            {result.change_plan.likely_code_path.join(' → ') || 'Static flow unavailable.'}
          </li>
          <li>
            <strong>Potentially affected files:</strong>{' '}
            {result.change_plan.potentially_affected_files.join(', ') || 'No resolved neighbors.'}
          </li>
          <li>
            <strong>Tests to review:</strong>{' '}
            {result.change_plan.tests_to_review.join(', ') || 'No likely persisted tests found.'}
          </li>
          <li>
            <strong>Risks and limitations:</strong>{' '}
            {result.change_plan.risks_and_limitations.join(' ')}
          </li>
        </ol>
      </section>
      <section className="limitations">
        <h3>Unknown or dynamic impact</h3>
        <p>{impact.unknown_dynamic_impact}</p>
        <ul>
          {result.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </section>
  )
}
