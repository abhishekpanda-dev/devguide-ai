import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import type {
  Analysis,
  CodeFindingsResponse,
  StructureFile,
  StructureResponse,
} from '../../api/types'
import { ApiErrorMessage } from '../feedback/ApiErrorMessage'
import {
  MAX_GRAPH_EDGES,
  MAX_GRAPH_NODES,
  sourceUrlForFile,
  transformDependencyData,
  type DependencyFilters,
} from './dependencyGraphData'

const DependencyGraph = lazy(() => import('./DependencyGraph'))
const DependencyBundle = lazy(() => import('./DependencyBundle'))
const EMPTY_FILTERS: DependencyFilters = {
  language: '',
  pathPrefix: '',
  relationshipType: '',
  entryPointsOnly: false,
  showIsolatedFiles: false,
}

function narrowScreen() {
  return typeof window !== 'undefined' && window.matchMedia?.('(max-width: 760px)').matches
}

export function DependencyVisualization({
  analysis,
  structure,
  findings,
  error,
}: {
  analysis: Analysis
  structure?: StructureResponse
  findings?: CodeFindingsResponse
  error?: unknown
}) {
  const [mode, setMode] = useState<'bundle' | 'flow' | 'tree'>(() =>
    narrowScreen() ? 'tree' : 'bundle',
  )
  const [colorMode, setColorMode] = useState<'language' | 'folder'>('language')
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string>()
  const [focusId, setFocusId] = useState<string>()
  const data = useMemo(
    () => (structure ? transformDependencyData(structure, filters) : undefined),
    [filters, structure],
  )
  const languages = useMemo(
    () => [...new Set(structure?.files.map((file) => file.language) ?? [])].sort(),
    [structure],
  )
  const searchResults = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    if (!query || !data) return []
    return data.files.filter((file) => file.path.toLocaleLowerCase().includes(query)).slice(0, 8)
  }, [data, search])
  const selected = data?.files.find((file) => file.repository_file_id === selectedId)
  const findingSeverityByPath = useMemo(() => {
    const mapped: Record<string, 'high' | 'warning'> = {}
    for (const finding of findings?.findings ?? []) {
      if (finding.severity !== 'high' && finding.severity !== 'warning') continue
      if (mapped[finding.path] !== 'high') mapped[finding.path] = finding.severity
    }
    return mapped
  }, [findings])
  const treeGroups = useMemo(() => {
    const groups = new Map<string, StructureFile[]>()
    for (const file of data?.files ?? []) {
      const segments = file.path.split('/')
      const folder = segments.length > 1 ? segments.slice(0, -1).join('/') : '(root)'
      groups.set(folder, [...(groups.get(folder) ?? []), file])
    }
    return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right))
  }, [data?.files])
  const sourceUrl =
    selected && structure
      ? sourceUrlForFile(selected.repository_file_id, structure.dependency_edges)
      : undefined
  const selectFile = useCallback((file: StructureFile) => {
    setSelectedId(file.repository_file_id)
    setFocusId(file.repository_file_id)
  }, [])
  useEffect(() => {
    const query = window.matchMedia?.('(max-width: 760px)')
    if (!query) return
    const handleChange = (event: MediaQueryListEvent) => {
      if (event.matches) setMode('tree')
    }
    query.addEventListener?.('change', handleChange)
    return () => query.removeEventListener?.('change', handleChange)
  }, [])
  const dependencies = useMemo(
    () =>
      selected && data
        ? data.edges
            .filter((edge) => edge.source_repository_file_id === selected.repository_file_id)
            .map((edge) => ({
              edge,
              file: data.files.find(
                (file) => file.repository_file_id === edge.target_repository_file_id,
              ),
            }))
            .filter((item): item is typeof item & { file: StructureFile } => Boolean(item.file))
        : [],
    [data, selected],
  )
  const dependents = useMemo(
    () =>
      selected && data
        ? data.edges
            .filter((edge) => edge.target_repository_file_id === selected.repository_file_id)
            .map((edge) => ({
              edge,
              file: data.files.find(
                (file) => file.repository_file_id === edge.source_repository_file_id,
              ),
            }))
            .filter((item): item is typeof item & { file: StructureFile } => Boolean(item.file))
        : [],
    [data, selected],
  )

  return (
    <section className="dependencyVisualization" aria-labelledby="dependency-heading">
      <div className="dependencyHeader">
        <div>
          <p className="panelLabel">Persisted static relationships</p>
          <h2 id="dependency-heading">Dependency visualization</h2>
        </div>
        <div className="dependencyModes" role="tablist" aria-label="Visualization mode">
          {(['bundle', 'flow', 'tree'] as const).map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={mode === item}
              onClick={() => setMode(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      {error ? (
        <ApiErrorMessage error={error} fallback="Dependency structure is unavailable." />
      ) : !structure ? (
        <p className="emptyCompact">Loading persisted dependency structure…</p>
      ) : !structure.files.length ? (
        <p className="emptyCompact">No persisted files are available for visualization.</p>
      ) : (
        <>
          <div className="dependencyFilters" aria-label="Dependency filters">
            <label>
              Language
              <select
                value={filters.language}
                onChange={(event) =>
                  setFilters((value) => ({ ...value, language: event.target.value }))
                }
              >
                <option value="">All languages</option>
                {languages.map((language) => (
                  <option key={language}>{language}</option>
                ))}
              </select>
            </label>
            <label>
              Path prefix
              <input
                value={filters.pathPrefix}
                onChange={(event) =>
                  setFilters((value) => ({ ...value, pathPrefix: event.target.value }))
                }
                placeholder="src/"
              />
            </label>
            <label>
              Relationship
              <select
                value={filters.relationshipType}
                onChange={(event) =>
                  setFilters((value) => ({ ...value, relationshipType: event.target.value }))
                }
              >
                <option value="">All relationships</option>
                <option value="imports">Imports</option>
                <option value="requires">Requires</option>
                <option value="reexports">Reexports</option>
              </select>
            </label>
            <label>
              Color by
              <select
                value={colorMode}
                onChange={(event) => setColorMode(event.target.value as 'language' | 'folder')}
              >
                <option value="language">Language</option>
                <option value="folder">Top folder</option>
              </select>
            </label>
            <label className="filterCheck">
              <input
                type="checkbox"
                checked={filters.entryPointsOnly}
                onChange={(event) =>
                  setFilters((value) => ({ ...value, entryPointsOnly: event.target.checked }))
                }
              />{' '}
              Entry points only
            </label>
            <label className="filterCheck">
              <input
                type="checkbox"
                checked={filters.showIsolatedFiles}
                onChange={(event) =>
                  setFilters((value) => ({
                    ...value,
                    showIsolatedFiles: event.target.checked,
                  }))
                }
              />{' '}
              Show isolated files
            </label>
          </div>
          <div className="dependencySearch">
            <label htmlFor="dependency-file-search">Find a file</label>
            <input
              id="dependency-file-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search persisted file paths"
            />
            {searchResults.length ? (
              <ul aria-label="File search results">
                {searchResults.map((file) => (
                  <li key={file.repository_file_id}>
                    <button
                      type="button"
                      onClick={() => {
                        selectFile(file)
                        setSearch('')
                      }}
                    >
                      <code>{file.path}</code>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          {data?.truncatedNodes || data?.truncatedEdges || data?.hiddenIsolated ? (
            <p className="graphNotice" role="status">
              Visualization bounded to {MAX_GRAPH_NODES} nodes and {MAX_GRAPH_EDGES} edges.{' '}
              {data.truncatedNodes} nodes and {data.truncatedEdges} edges are not rendered.
              {data.hiddenIsolated ? ` ${data.hiddenIsolated} isolated files are hidden.` : ''}
            </p>
          ) : null}
          {!data?.files.length ? (
            <p className="emptyCompact">No files match the active visualization filters.</p>
          ) : (
            <div className="dependencyStage">
              <div className="dependencyPrimary">
                <p className="srOnly">
                  Showing {data.files.length} persisted files and {data.edges.length} directed
                  dependency relationships. Isolated files are{' '}
                  {filters.showIsolatedFiles ? 'shown' : 'hidden by default'}.
                </p>
                {mode === 'bundle' && (
                  <div className="desktopBundleMode">
                    <Suspense fallback={<p className="emptyCompact">Loading bundle rendererâ€¦</p>}>
                      <DependencyBundle
                        files={data.files}
                        edges={data.edges}
                        selectedId={selectedId}
                        focusId={focusId}
                        colorMode={colorMode}
                        onSelect={selectFile}
                      />
                    </Suspense>
                  </div>
                )}
                {mode === 'flow' && (
                  <div className="desktopGraphMode">
                    <Suspense fallback={<p className="emptyCompact">Loading graph renderer…</p>}>
                      <DependencyGraph
                        files={data.files}
                        edges={data.edges}
                        selectedId={selectedId}
                        focusId={focusId}
                        colorMode={colorMode}
                        findingSeverityByPath={findingSeverityByPath}
                        onSelect={selectFile}
                      />
                    </Suspense>
                  </div>
                )}
                {mode === 'tree' && (
                  <div className="dependencyTree">
                    <ul aria-label="Repository dependency tree">
                      {treeGroups.map(([folder, files]) => (
                        <li className="dependencyTreeGroup" key={folder}>
                          <details open>
                            <summary>
                              <span aria-hidden="true">▾</span> <code>{folder}</code>
                            </summary>
                            <ul>
                              {files
                                .slice()
                                .sort((left, right) => left.path.localeCompare(right.path))
                                .map((file) => (
                                  <li key={file.repository_file_id}>
                                    <button
                                      type="button"
                                      aria-pressed={selectedId === file.repository_file_id}
                                      onClick={() => selectFile(file)}
                                    >
                                      <span aria-hidden="true">
                                        {file.is_entry_point ? '◆' : '·'}
                                      </span>
                                      <code>{file.path.split('/').at(-1)}</code>
                                      <span>
                                        {findingSeverityByPath[file.path]
                                          ? `${findingSeverityByPath[file.path]} finding · `
                                          : ''}
                                        {file.total_dependency_count} connections
                                      </span>
                                    </button>
                                  </li>
                                ))}
                            </ul>
                          </details>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {!data.edges.length && (
                  <p className="graphNotice">
                    No persisted dependency edges match this view. File nodes remain available.
                  </p>
                )}
              </div>
              {selected ? (
                <aside
                  className="nodeDetails"
                  aria-label="Selected file details"
                  aria-live="polite"
                >
                  <div className="cardHeading">
                    <h3>Selected file</h3>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedId(undefined)
                        setFocusId(undefined)
                      }}
                    >
                      Clear selection
                    </button>
                  </div>
                  <code>{selected.path}</code>
                  {selected.is_entry_point && (
                    <span className="entryPointBadge">Probable entry point</span>
                  )}
                  <dl>
                    <div>
                      <dt>Language</dt>
                      <dd>{selected.language}</dd>
                    </div>
                    <div>
                      <dt>Classification</dt>
                      <dd>{selected.classification}</dd>
                    </div>
                    <div>
                      <dt>Lines</dt>
                      <dd>{selected.line_count}</dd>
                    </div>
                    <div>
                      <dt>Inbound</dt>
                      <dd>{selected.inbound_dependency_count}</dd>
                    </div>
                    <div>
                      <dt>Outbound</dt>
                      <dd>{selected.outbound_dependency_count}</dd>
                    </div>
                    <div>
                      <dt>Total</dt>
                      <dd>{selected.total_dependency_count}</dd>
                    </div>
                  </dl>
                  {selected.entry_point_reason && <p>{selected.entry_point_reason}</p>}
                  <div className="nodeRelationshipLists">
                    <section aria-labelledby="dependencies-heading">
                      <h4 id="dependencies-heading">Dependencies</h4>
                      {dependencies.length ? (
                        <ul>
                          {dependencies.map(({ edge, file }) => (
                            <li key={edge.id}>
                              <button type="button" onClick={() => selectFile(file)}>
                                <code>{file.path}</code>
                                <span>{edge.relationship_type}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="emptyCompact">No rendered outgoing dependencies.</p>
                      )}
                    </section>
                    <section aria-labelledby="dependents-heading">
                      <h4 id="dependents-heading">Dependents</h4>
                      {dependents.length ? (
                        <ul>
                          {dependents.map(({ edge, file }) => (
                            <li key={edge.id}>
                              <button type="button" onClick={() => selectFile(file)}>
                                <code>{file.path}</code>
                                <span>{edge.relationship_type}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="emptyCompact">No rendered incoming dependents.</p>
                      )}
                    </section>
                  </div>
                  {sourceUrl ? (
                    <a href={sourceUrl} target="_blank" rel="noopener noreferrer">
                      Open exact source
                    </a>
                  ) : (
                    <p className="emptyCompact">
                      An exact persisted source link is unavailable for this file.
                    </p>
                  )}
                  <Link
                    to={`/analyses/${analysis.id}/ask?path=${encodeURIComponent(selected.path)}`}
                  >
                    Ask DevGuide about this file
                  </Link>
                  <Link to={`/analyses/${analysis.id}/structure`}>Open Structure page</Link>
                </aside>
              ) : null}
            </div>
          )}
        </>
      )}
    </section>
  )
}
