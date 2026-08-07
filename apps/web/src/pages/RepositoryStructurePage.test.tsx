import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RepositoryStructurePage } from './RepositoryStructurePage'
import { jsonResponse, renderRoute } from '../test/test-utils'

const file = {
  repository_file_id: 'f1',
  path: 'src/main.ts',
  language: 'typescript',
  classification: 'source',
  line_count: 10,
  content_hash: 'a'.repeat(64),
  commit_sha: 'b'.repeat(40),
  is_entry_point: true,
  entry_point_reason: 'package.json main field.',
  entry_point_confidence: 1,
  inbound_dependency_count: 0,
  outbound_dependency_count: 1,
  total_dependency_count: 1,
}
const target = {
  ...file,
  repository_file_id: 'f2',
  path: 'src/service.ts',
  is_entry_point: false,
  entry_point_reason: null,
  entry_point_confidence: 0,
  inbound_dependency_count: 1,
  outbound_dependency_count: 0,
}
const response = {
  analysis_job_id: 'a1',
  repository: { id: 'r1', owner: 'acme', name: 'project', commit_sha: 'b'.repeat(40) },
  files: [file, target],
  entry_points: [file],
  limitations: [],
  dependency_edges: [
    {
      id: 'e1',
      source_repository_file_id: 'f1',
      target_repository_file_id: 'f2',
      relationship_type: 'imports',
      module_name: './service',
      source_path: file.path,
      target_path: target.path,
      source_line: 2,
      confidence: 1,
      source_url: `https://github.com/acme/project/blob/${'b'.repeat(40)}/src/main.ts#L2`,
    },
  ],
  summary: {
    file_count: 2,
    directory_count: 1,
    language_counts: { typescript: 2 },
    edge_count: 1,
    entry_point_count: 1,
    highest_inbound_files: [target],
    highest_outbound_files: [file],
    most_connected_files: [file, target],
  },
}

test('renders language entry points coupling dependency evidence and accessible filters', async () => {
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(response))
  const user = userEvent.setup()
  renderRoute(
    <RepositoryStructurePage />,
    '/analyses/a1/structure',
    '/analyses/:analysisId/structure',
  )
  expect(await screen.findByText('Repository Structure')).toBeInTheDocument()
  expect(screen.getAllByText('src/main.ts').length).toBeGreaterThan(0)
  expect(screen.getAllByText('src/service.ts').length).toBeGreaterThan(0)
  expect(screen.getByText(/package\.json main field\./)).toBeInTheDocument()
  const link = screen.getByRole('link', { name: 'Line 2' })
  expect(link).toHaveAttribute('href', response.dependency_edges[0].source_url)
  await user.selectOptions(screen.getByLabelText('Language'), 'typescript')
  await user.type(screen.getByLabelText('Path prefix'), 'src')
  await user.selectOptions(screen.getByLabelText('Relationship'), 'imports')
  await waitFor(() => {
    expect(spy.mock.calls.some(([url]) => String(url).includes('language=typescript'))).toBe(true)
    expect(spy.mock.calls.some(([url]) => String(url).includes('path_prefix=src'))).toBe(true)
    expect(spy.mock.calls.some(([url]) => String(url).includes('relationship_type=imports'))).toBe(
      true,
    )
  })
})

test('renders loading empty and safe API error states', async () => {
  const pending = new Promise<Response>(() => undefined)
  vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() => pending)
  const first = renderRoute(
    <RepositoryStructurePage />,
    '/analyses/a1/structure',
    '/analyses/:analysisId/structure',
  )
  expect(screen.getByRole('status')).toHaveTextContent('Loading repository structure')
  first.unmount()
  vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() =>
    jsonResponse({ ...response, dependency_edges: [] }),
  )
  const second = renderRoute(
    <RepositoryStructurePage />,
    '/analyses/a1/structure',
    '/analyses/:analysisId/structure',
  )
  expect(await screen.findByText('No local dependencies')).toBeInTheDocument()
  second.unmount()
  vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() =>
    jsonResponse(
      {
        error: {
          code: 'analysis_not_ready',
          message: 'Structure is not ready.',
          correlation_id: 'structure-1',
        },
      },
      409,
    ),
  )
  renderRoute(
    <RepositoryStructurePage />,
    '/analyses/a1/structure',
    '/analyses/:analysisId/structure',
  )
  expect(await screen.findByText('Structure is not ready.')).toBeInTheDocument()
  expect(screen.getByText(/structure-1/)).toBeInTheDocument()
})
