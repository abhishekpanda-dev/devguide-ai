import { useEffect, useMemo, useState } from 'react'
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { StructureEdge, StructureFile } from '../../api/types'

const LANGUAGE_COLORS = ['#4da3ff', '#18d47b', '#a97cff', '#f59e42', '#ff6b8a', '#57c7d4']

function colorFor(value: string) {
  let hash = 0
  for (const character of value) hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  return LANGUAGE_COLORS[hash % LANGUAGE_COLORS.length]
}

function folderFor(path: string) {
  const segments = path.split('/')
  return segments.length > 1 ? segments[0] : '(root)'
}

function fileName(path: string) {
  return path.split('/').at(-1) ?? path
}

export default function DependencyGraph({
  files,
  edges,
  selectedId,
  focusId,
  colorMode,
  findingSeverityByPath,
  onSelect,
}: {
  files: StructureFile[]
  edges: StructureEdge[]
  selectedId?: string
  focusId?: string
  colorMode: 'language' | 'folder'
  findingSeverityByPath: Record<string, 'high' | 'warning'>
  onSelect: (file: StructureFile) => void
}) {
  const [instance, setInstance] = useState<ReactFlowInstance<Node, Edge>>()
  const connectedEdgeIds = useMemo(
    () =>
      new Set(
        selectedId
          ? edges
              .filter(
                (edge) =>
                  edge.source_repository_file_id === selectedId ||
                  edge.target_repository_file_id === selectedId,
              )
              .map((edge) => edge.id)
          : [],
      ),
    [edges, selectedId],
  )
  const connectedNodeIds = useMemo(
    () =>
      new Set(
        selectedId
          ? edges.flatMap((edge) =>
              edge.source_repository_file_id === selectedId
                ? [edge.target_repository_file_id]
                : edge.target_repository_file_id === selectedId
                  ? [edge.source_repository_file_id]
                  : [],
            )
          : [],
      ),
    [edges, selectedId],
  )
  const nodes = useMemo<Node[]>(
    () =>
      files.map((file, index) => {
        const column = index % 5
        const row = Math.floor(index / 5)
        const color = colorFor(colorMode === 'language' ? file.language : folderFor(file.path))
        const findingSeverity = findingSeverityByPath[file.path]
        const size = Math.min(150, Math.max(104, 104 + file.total_dependency_count * 4))
        return {
          id: file.repository_file_id,
          position: { x: column * 190, y: row * 120 },
          data: {
            label: (
              <button
                type="button"
                className="dependencyNodeButton"
                title={`${file.path} · ${file.language} · ${file.total_dependency_count} dependencies`}
                onClick={() => onSelect(file)}
              >
                <span>
                  {file.is_entry_point ? 'Entry · ' : ''}
                  {findingSeverity ? `${findingSeverity} finding · ` : ''}
                  {file.language}
                </span>
                <code>{fileName(file.path)}</code>
                <small>{folderFor(file.path)}</small>
              </button>
            ),
          },
          selected: file.repository_file_id === selectedId,
          style: {
            width: size,
            borderColor: color,
            boxShadow: file.is_entry_point ? `inset 3px 0 0 ${color}` : undefined,
            opacity:
              selectedId &&
              file.repository_file_id !== selectedId &&
              !connectedNodeIds.has(file.repository_file_id)
                ? 0.38
                : 1,
          },
          ariaLabel: `${file.path}, ${file.language}, ${file.total_dependency_count} dependencies${file.is_entry_point ? ', probable entry point' : ''}${findingSeverity ? `, ${findingSeverity} finding` : ''}`,
        }
      }),
    [colorMode, connectedNodeIds, files, findingSeverityByPath, onSelect, selectedId],
  )
  const flowEdges = useMemo<Edge[]>(
    () =>
      edges.map((edge) => ({
        id: edge.id,
        source: edge.source_repository_file_id,
        target: edge.target_repository_file_id,
        label: edge.relationship_type,
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        animated: false,
        className: connectedEdgeIds.has(edge.id) ? 'dependencyEdgeSelected' : undefined,
        style: {
          strokeWidth: connectedEdgeIds.has(edge.id) ? 2 : 1,
          opacity: selectedId && !connectedEdgeIds.has(edge.id) ? 0.16 : 1,
          stroke:
            edge.relationship_type === 'reexports'
              ? '#a97cff'
              : edge.relationship_type === 'requires'
                ? '#18d47b'
                : '#4d6f91',
        },
      })),
    [connectedEdgeIds, edges, selectedId],
  )

  useEffect(() => {
    if (focusId && instance)
      void instance.fitView({ nodes: [{ id: focusId }], duration: 250, maxZoom: 1.5, padding: 0.8 })
  }, [focusId, instance])

  return (
    <div className="dependencyGraphCanvas" aria-label="Repository dependency flow">
      <ReactFlow
        nodes={nodes}
        edges={flowEdges}
        onInit={setInstance}
        onNodeClick={(_, node) => {
          const file = files.find((item) => item.repository_file_id === node.id)
          if (file) onSelect(file)
        }}
        fitView
        fitViewOptions={{ padding: 0.25, maxZoom: 1.2 }}
        minZoom={0.25}
        maxZoom={2}
        nodesDraggable={false}
        nodesFocusable
        edgesFocusable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#252b35" gap={24} size={1} />
        <Controls showInteractive={false} aria-label="Graph zoom and fit controls" />
      </ReactFlow>
    </div>
  )
}
