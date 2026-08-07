import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { getRepositoryStructure } from '../api/analyses'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'

export function RepositoryStructurePage() {
  const { analysisId = '' } = useParams()
  const [language, setLanguage] = useState('')
  const [pathPrefix, setPathPrefix] = useState('')
  const [relationshipType, setRelationshipType] = useState('')
  const query = useQuery({
    queryKey: ['repository-structure', analysisId, language, pathPrefix, relationshipType],
    queryFn: () =>
      getRepositoryStructure(analysisId, {
        language: language || undefined,
        pathPrefix: pathPrefix || undefined,
        relationshipType: relationshipType || undefined,
      }),
    enabled: Boolean(analysisId),
    placeholderData: (previous) => previous,
  })
  if (query.isPending)
    return (
      <div className="state" role="status">
        Loading repository structure…
      </div>
    )
  if (query.isError)
    return (
      <ApiErrorMessage error={query.error} fallback="Repository structure could not be loaded." />
    )
  return (
    <div>
      <p className="eyebrow">Deterministic static evidence</p>
      <h1>Repository Structure</h1>
      <p className="lede">
        Probable entry points and repository-local dependencies. Static edges do not prove runtime
        behavior.
      </p>
      <div className="findingFilters" aria-label="Structure filters">
        <label htmlFor="structure-language">
          Language
          <select
            id="structure-language"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            <option value="">All</option>
            {Object.keys(query.data.summary.language_counts).map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="structure-path">
          Path prefix
          <input
            id="structure-path"
            value={pathPrefix}
            onChange={(event) => setPathPrefix(event.target.value)}
          />
        </label>
        <label htmlFor="structure-relationship">
          Relationship
          <select
            id="structure-relationship"
            value={relationshipType}
            onChange={(event) => setRelationshipType(event.target.value)}
          >
            <option value="">All</option>
            <option value="imports">Imports</option>
            <option value="requires">Requires</option>
            <option value="reexports">Reexports</option>
          </select>
        </label>
      </div>
      <section className="panel">
        <h2>Languages</h2>
        <ul>
          {Object.entries(query.data.summary.language_counts).map(([name, count]) => (
            <li key={name}>
              <strong>{name}</strong>: {count} files
            </li>
          ))}
        </ul>
      </section>
      <section className="panel">
        <h2>Probable entry points</h2>
        {query.data.entry_points.length ? (
          <ul>
            {query.data.entry_points.map((file) => (
              <li key={file.path}>
                <code>{file.path}</code> — {file.entry_point_reason} (
                {Math.round(file.entry_point_confidence * 100)}% confidence)
              </li>
            ))}
          </ul>
        ) : (
          <p>No probable entry points were identified.</p>
        )}
      </section>
      <section className="panel">
        <h2>Most connected files</h2>
        <ul>
          {query.data.summary.most_connected_files.map((file) => (
            <li key={file.path}>
              <code>{file.path}</code> — {file.inbound_dependency_count} inbound,{' '}
              {file.outbound_dependency_count} outbound
            </li>
          ))}
        </ul>
      </section>
      <section className="panel">
        <h2>Dependencies</h2>
        {query.data.dependency_edges.length ? (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Relationship</th>
                  <th>Target</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {query.data.dependency_edges.map((edge) => (
                  <tr key={edge.id}>
                    <td>
                      <code>{edge.source_path}</code>
                    </td>
                    <td>{edge.relationship_type}</td>
                    <td>
                      <code>{edge.target_path}</code>
                    </td>
                    <td>
                      <a href={edge.source_url} target="_blank" rel="noopener noreferrer">
                        Line {edge.source_line}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="emptyState">
            <h3>No local dependencies</h3>
            <p>No resolved dependency edges match these filters.</p>
          </div>
        )}
      </section>
      {query.data.limitations.length ? (
        <aside className="limitations">
          <h2>Limitations</h2>
          <ul>
            {query.data.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </aside>
      ) : null}
      <p className="backLink">
        <Link to={`/analyses/${analysisId}`}>Back to analysis</Link>
      </p>
    </div>
  )
}
