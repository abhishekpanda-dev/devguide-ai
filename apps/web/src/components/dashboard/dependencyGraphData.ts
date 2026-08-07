import type { StructureEdge, StructureFile, StructureResponse } from '../../api/types'

export const MAX_GRAPH_NODES = 80
export const MAX_GRAPH_EDGES = 160

export interface DependencyFilters {
  language: string
  pathPrefix: string
  relationshipType: string
  entryPointsOnly: boolean
  showIsolatedFiles: boolean
}

export interface BoundedDependencyData {
  files: StructureFile[]
  edges: StructureEdge[]
  truncatedNodes: number
  truncatedEdges: number
  hiddenIsolated: number
}

export function transformDependencyData(
  structure: StructureResponse,
  filters: DependencyFilters,
): BoundedDependencyData {
  const trustedTargets = new Set(structure.files.map((file) => file.repository_file_id))
  const resolvedEdges = structure.dependency_edges.filter(
    (edge) =>
      trustedTargets.has(edge.source_repository_file_id) &&
      trustedTargets.has(edge.target_repository_file_id),
  )
  const relationshipEdges = resolvedEdges.filter(
    (edge) => !filters.relationshipType || edge.relationship_type === filters.relationshipType,
  )
  const connectedIds = new Set(
    relationshipEdges.flatMap((edge) => [
      edge.source_repository_file_id,
      edge.target_repository_file_id,
    ]),
  )
  const normalizedPrefix = filters.pathPrefix.trim().toLocaleLowerCase()
  const filteredFiles = structure.files
    .filter((file) => !filters.language || file.language === filters.language)
    .filter(
      (file) => !normalizedPrefix || file.path.toLocaleLowerCase().startsWith(normalizedPrefix),
    )
    .filter((file) => !filters.entryPointsOnly || file.is_entry_point)
  const matchingFiles = filteredFiles
    .filter(
      (file) =>
        filters.showIsolatedFiles ||
        relationshipEdges.length === 0 ||
        connectedIds.has(file.repository_file_id) ||
        file.is_entry_point ||
        file.total_dependency_count > 0,
    )
    .sort(
      (left, right) =>
        right.total_dependency_count - left.total_dependency_count ||
        left.path.localeCompare(right.path),
    )
  const files = matchingFiles.slice(0, MAX_GRAPH_NODES)
  const renderedIds = new Set(files.map((file) => file.repository_file_id))
  const matchingEdges = relationshipEdges
    .filter(
      (edge) =>
        renderedIds.has(edge.source_repository_file_id) &&
        renderedIds.has(edge.target_repository_file_id),
    )
    .sort(
      (left, right) =>
        left.source_path.localeCompare(right.source_path) ||
        left.target_path.localeCompare(right.target_path) ||
        left.id.localeCompare(right.id),
    )
  const edges = matchingEdges.slice(0, MAX_GRAPH_EDGES)
  return {
    files,
    edges,
    truncatedNodes: Math.max(0, matchingFiles.length - files.length),
    truncatedEdges: Math.max(0, matchingEdges.length - edges.length),
    hiddenIsolated: Math.max(0, filteredFiles.length - matchingFiles.length),
  }
}

export function sourceUrlForFile(fileId: string, edges: StructureEdge[]) {
  return edges.find((edge) => edge.source_repository_file_id === fileId)?.source_url
}
