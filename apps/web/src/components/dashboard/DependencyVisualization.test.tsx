import type { ReactNode } from 'react'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import type { Analysis, StructureResponse } from '../../api/types'
import { DependencyVisualization } from './DependencyVisualization'
import { MAX_GRAPH_EDGES, MAX_GRAPH_NODES, transformDependencyData } from './dependencyGraphData'

vi.mock('@xyflow/react', () => ({
  ReactFlow: ({
    nodes,
    edges,
    children,
  }: {
    nodes: Array<{ id: string; data: { label: ReactNode } }>
    edges: Array<{ id: string; label: string }>
    children: ReactNode
  }) => (
    <div aria-label="Repository dependency flow">
      {nodes.map((node) => (
        <div data-testid={`graph-node-${node.id}`} key={node.id}>
          {node.data.label}
        </div>
      ))}
      {edges.map((edge) => (
        <div data-testid={`graph-edge-${edge.id}`} key={edge.id}>
          {edge.label}
        </div>
      ))}
      {children}
    </div>
  ),
  Background: () => null,
  Controls: () => <div role="group" aria-label="Graph zoom and fit controls" />,
  MarkerType: { ArrowClosed: 'arrowclosed' },
}))

const analysis = { id: 'a1' } as Analysis
const file = (id: string, path: string, language: string, dependencies: number, entry = false) => ({
  repository_file_id: id,
  path,
  language,
  classification: 'source',
  line_count: 42,
  content_hash: id.repeat(64).slice(0, 64),
  commit_sha: 'b'.repeat(40),
  is_entry_point: entry,
  entry_point_reason: entry ? 'Application bootstrap.' : null,
  entry_point_confidence: entry ? 1 : 0,
  inbound_dependency_count: Math.max(0, dependencies - 1),
  outbound_dependency_count: dependencies ? 1 : 0,
  total_dependency_count: dependencies,
})
const main = file('1', 'src/main.ts', 'typescript', 2, true)
const service = file('2', 'src/service.ts', 'typescript', 1)
const config = file('3', 'config/settings.py', 'python', 0)
const structure: StructureResponse = {
  analysis_job_id: 'a1',
  repository: { id: 'r1', owner: 'acme', name: 'project', commit_sha: 'b'.repeat(40) },
  files: [main, service, config],
  dependency_edges: [
    {
      id: 'e1',
      source_repository_file_id: '1',
      target_repository_file_id: '2',
      relationship_type: 'imports',
      module_name: './service',
      source_path: main.path,
      target_path: service.path,
      source_line: 2,
      confidence: 1,
      source_url: 'https://github.com/acme/project/blob/b/src/main.ts#L2',
    },
    {
      id: 'e2',
      source_repository_file_id: '2',
      target_repository_file_id: '1',
      relationship_type: 'reexports',
      module_name: './main',
      source_path: service.path,
      target_path: main.path,
      source_line: 8,
      confidence: 1,
      source_url: 'https://github.com/acme/project/blob/b/src/service.ts#L8',
    },
  ],
  entry_points: [main],
  summary: {
    file_count: 3,
    directory_count: 2,
    language_counts: { typescript: 2, python: 1 },
    edge_count: 2,
    entry_point_count: 1,
    highest_inbound_files: [main],
    highest_outbound_files: [main],
    most_connected_files: [main],
  },
  limitations: [],
}

function renderVisualization(value: StructureResponse = structure, error?: unknown, route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <DependencyVisualization analysis={analysis} structure={value} error={error} />
    </MemoryRouter>,
  )
}

test('focus query selects the persisted matching file without trusting a client file id', async () => {
  renderVisualization(structure, undefined, '/?focus=src%2Fservice.ts')
  const details = await screen.findByLabelText('Selected file details')
  expect(details).toHaveTextContent('src/service.ts')
  expect(details).toHaveTextContent('Dependencies')
})

test('defaults to Bundle with real persisted nodes and edges and preserves Flow and Tree', async () => {
  const { container } = renderVisualization()
  expect(screen.getByRole('tab', { name: 'bundle' })).toHaveAttribute('aria-selected', 'true')
  expect(
    await screen.findByRole('img', {
      name: '2 persisted files and 2 directed dependency relationships in a radial bundle',
    }),
  ).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /src\/main\.ts, 2 dependencies/i })).toBeInTheDocument()
  expect(container.querySelectorAll('.bundleEdges path')).toHaveLength(2)
  const flowTab = screen.getByRole('tab', { name: 'flow' })
  await userEvent.click(flowTab)
  expect(await screen.findByTestId('graph-node-1')).toHaveTextContent('main.ts')
  expect(screen.getByTestId('graph-edge-e1')).toHaveTextContent('imports')
  expect(screen.getByRole('group', { name: 'Graph zoom and fit controls' })).toBeInTheDocument()
  const treeTab = screen.getByRole('tab', { name: 'tree' })
  await userEvent.click(treeTab)
  expect(treeTab).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByLabelText('Repository dependency tree')).toBeInTheDocument()
})

test('selects an entry point and shows trusted details and actions', async () => {
  const { container } = renderVisualization()
  await userEvent.click(
    await screen.findByRole('button', { name: /src\/main\.ts, 2 dependencies/i }),
  )
  const details = screen.getByLabelText('Selected file details')
  expect(details).toHaveTextContent('Probable entry point')
  expect(details).toHaveTextContent('Application bootstrap.')
  expect(within(details).getByRole('heading', { name: 'Dependencies' })).toBeInTheDocument()
  expect(within(details).getByRole('heading', { name: 'Dependents' })).toBeInTheDocument()
  expect(
    within(details).getByRole('button', { name: /src\/service\.ts imports/i }),
  ).toBeInTheDocument()
  expect(container.querySelectorAll('.bundleOutgoing')).toHaveLength(1)
  expect(container.querySelectorAll('.bundleIncoming')).toHaveLength(1)
  expect(within(details).getByRole('link', { name: 'Open exact source' })).toHaveAttribute(
    'href',
    structure.dependency_edges[0].source_url,
  )
  expect(
    within(details).getByRole('link', { name: 'Ask DevGuide about this file' }),
  ).toHaveAttribute('href', '/analyses/a1/ask?path=src%2Fmain.ts')
  expect(within(details).getByRole('link', { name: 'Open Structure page' })).toHaveAttribute(
    'href',
    '/analyses/a1/structure',
  )
})

test('filters by language and relationship without mutating persisted data', async () => {
  renderVisualization()
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('Show isolated files'))
  await user.selectOptions(screen.getByLabelText('Language'), 'python')
  expect(
    await screen.findByRole('button', { name: /config\/settings\.py, 0 dependencies/i }),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: /src\/main\.ts, 2 dependencies/i }),
  ).not.toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText('Language'), '')
  await user.selectOptions(screen.getByLabelText('Relationship'), 'reexports')
  await user.click(screen.getByRole('tab', { name: 'flow' }))
  expect(await screen.findByTestId('graph-edge-e2')).toBeInTheDocument()
  expect(screen.queryByTestId('graph-edge-e1')).not.toBeInTheDocument()
  expect(structure.files).toHaveLength(3)
  expect(structure.dependency_edges).toHaveLength(2)
})

test('searches paths case-insensitively and focuses a selected result', async () => {
  renderVisualization()
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Find a file'), 'SERVICE.TS')
  const results = screen.getByLabelText('File search results')
  await user.click(within(results).getByRole('button', { name: 'src/service.ts' }))
  expect(screen.getByLabelText('Selected file details')).toHaveTextContent('src/service.ts')
})

test('handles empty files, zero edges, and structure errors locally', async () => {
  const { rerender } = renderVisualization({ ...structure, files: [], dependency_edges: [] })
  expect(
    screen.getByText('No persisted files are available for visualization.'),
  ).toBeInTheDocument()
  rerender(
    <MemoryRouter>
      <DependencyVisualization
        analysis={analysis}
        structure={{ ...structure, dependency_edges: [] }}
      />
    </MemoryRouter>,
  )
  expect(
    await screen.findByText(
      'No persisted dependency edges match this view. File nodes remain available.',
    ),
  ).toBeInTheDocument()
  rerender(
    <MemoryRouter>
      <DependencyVisualization
        analysis={analysis}
        structure={structure}
        error={new Error('offline')}
      />
    </MemoryRouter>,
  )
  expect(screen.getByText('Dependency structure is unavailable.')).toBeInTheDocument()
})

test('bounds deterministic data and reports truncation', () => {
  const files = Array.from({ length: MAX_GRAPH_NODES + 2 }, (_, index) =>
    file(
      String(index + 10),
      `src/file-${index.toString().padStart(3, '0')}.ts`,
      'typescript',
      index,
    ),
  )
  const edges = Array.from({ length: MAX_GRAPH_EDGES + 2 }, (_, index) => ({
    ...structure.dependency_edges[0],
    id: `edge-${index.toString().padStart(3, '0')}`,
    source_repository_file_id: files[index % files.length].repository_file_id,
    target_repository_file_id: files[(index + 1) % files.length].repository_file_id,
    source_path: files[index % files.length].path,
    target_path: files[(index + 1) % files.length].path,
  }))
  const bounded = transformDependencyData(
    { ...structure, files, dependency_edges: edges },
    {
      language: '',
      pathPrefix: '',
      relationshipType: '',
      entryPointsOnly: false,
      showIsolatedFiles: true,
    },
  )
  expect(bounded.files).toHaveLength(MAX_GRAPH_NODES)
  expect(bounded.edges.length).toBeLessThanOrEqual(MAX_GRAPH_EDGES)
  expect(bounded.truncatedNodes).toBe(2)
})

test('hides isolated files by default and exposes them on request', async () => {
  renderVisualization()
  expect(
    await screen.findByRole('img', {
      name: '2 persisted files and 2 directed dependency relationships in a radial bundle',
    }),
  ).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('1 isolated files are hidden')
  await userEvent.click(screen.getByLabelText('Show isolated files'))
  expect(
    await screen.findByRole('img', {
      name: '3 persisted files and 2 directed dependency relationships in a radial bundle',
    }),
  ).toBeInTheDocument()
})

test('uses Tree as the mobile default', () => {
  const originalMatchMedia = window.matchMedia
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true,
    media: '(max-width: 760px)',
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }) as typeof window.matchMedia
  renderVisualization()
  expect(screen.getByRole('tab', { name: 'tree' })).toHaveAttribute('aria-selected', 'true')
  window.matchMedia = originalMatchMedia
})

test('shows a visible truncation notice for an oversized persisted response', async () => {
  const files = Array.from({ length: MAX_GRAPH_NODES + 2 }, (_, index) =>
    file(String(index + 100), `src/large-${index}.ts`, 'typescript', index),
  )
  renderVisualization({ ...structure, files, dependency_edges: [] })
  expect(await screen.findByRole('status')).toHaveTextContent(
    `Visualization bounded to ${MAX_GRAPH_NODES} nodes and ${MAX_GRAPH_EDGES} edges`,
  )
  expect(screen.getByRole('status')).toHaveTextContent('2 nodes')
})
