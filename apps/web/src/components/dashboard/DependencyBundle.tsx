import { useMemo, useRef, useState, type PointerEvent, type WheelEvent } from 'react'
import { cluster, hierarchy, type HierarchyPointNode } from 'd3-hierarchy'
import { arc, curveBundle, lineRadial } from 'd3-shape'
import type { StructureEdge, StructureFile } from '../../api/types'

const COLORS = ['#4da3ff', '#18d47b', '#a97cff', '#f59e42', '#ff6b8a', '#57c7d4']
const WIDTH = 900
const HEIGHT = 640
const RADIUS = 238

interface BundleDatum {
  name: string
  children?: BundleDatum[]
  file?: StructureFile
}

function colorFor(value: string) {
  let hash = 0
  for (const character of value) hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  return COLORS[hash % COLORS.length]
}

function topFolder(path: string) {
  const segments = path.split('/')
  return segments.length > 1 ? segments[0] : '(root)'
}

function shortName(path: string) {
  return path.split('/').at(-1) ?? path
}

function buildHierarchy(files: StructureFile[]): BundleDatum {
  const root: BundleDatum = { name: 'repository', children: [] }
  for (const file of files.slice().sort((left, right) => left.path.localeCompare(right.path))) {
    const segments = file.path.split('/')
    let current = root
    for (const segment of segments.slice(0, -1)) {
      current.children ??= []
      let child = current.children.find((item) => item.name === segment && !item.file)
      if (!child) {
        child = { name: segment, children: [] }
        current.children.push(child)
      }
      current = child
    }
    current.children ??= []
    current.children.push({ name: segments.at(-1) ?? file.path, file })
  }
  return root
}

export default function DependencyBundle({
  files,
  edges,
  selectedId,
  focusId,
  colorMode,
  onSelect,
}: {
  files: StructureFile[]
  edges: StructureEdge[]
  selectedId?: string
  focusId?: string
  colorMode: 'language' | 'folder'
  onSelect: (file: StructureFile) => void
}) {
  const [hoveredId, setHoveredId] = useState<string>()
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 })
  const drag = useRef<{ x: number; y: number; viewX: number; viewY: number } | undefined>(undefined)
  const layout = useMemo(() => {
    const root = hierarchy(buildHierarchy(files)).sort((left, right) =>
      left.data.name.localeCompare(right.data.name),
    )
    const positioned = cluster<BundleDatum>().size([Math.PI * 2, RADIUS])(root)
    const leaves = positioned.leaves().filter((node) => node.data.file)
    const byId = new Map(
      leaves.map((node) => [node.data.file?.repository_file_id ?? '', node] as const),
    )
    return { root: positioned, leaves, byId }
  }, [files])
  const edgePaths = useMemo(() => {
    const route = lineRadial<HierarchyPointNode<BundleDatum>>()
      .angle((node) => node.x)
      .radius((node) => node.y)
      .curve(curveBundle.beta(0.84))
    return edges.flatMap((edge) => {
      const source = layout.byId.get(edge.source_repository_file_id)
      const target = layout.byId.get(edge.target_repository_file_id)
      if (!source || !target) return []
      return [{ edge, path: route(source.path(target)) ?? '' }]
    })
  }, [edges, layout.byId])
  const activeId = hoveredId ?? selectedId ?? focusId
  const outgoingIds = useMemo(
    () =>
      new Set(
        activeId
          ? edges
              .filter((edge) => edge.source_repository_file_id === activeId)
              .map((edge) => edge.target_repository_file_id)
          : [],
      ),
    [activeId, edges],
  )
  const incomingIds = useMemo(
    () =>
      new Set(
        activeId
          ? edges
              .filter((edge) => edge.target_repository_file_id === activeId)
              .map((edge) => edge.source_repository_file_id)
          : [],
      ),
    [activeId, edges],
  )
  const sectors = useMemo(() => {
    const sectorArc = arc()
    return (layout.root.children ?? []).flatMap((group) => {
      const leaves = group.leaves()
      if (!leaves.length) return []
      const padding = 0.012
      const start = Math.min(...leaves.map((leaf) => leaf.x)) - padding
      const end = Math.max(...leaves.map((leaf) => leaf.x)) + padding
      return [
        {
          name: group.data.name,
          color: colorFor(group.data.name),
          path:
            sectorArc({
              innerRadius: RADIUS - 11,
              outerRadius: RADIUS - 4,
              startAngle: start,
              endAngle: end,
            }) ?? '',
        },
      ]
    })
  }, [layout.root])
  const onWheel = (event: WheelEvent<SVGSVGElement>) => {
    event.preventDefault()
    setView((current) => ({
      ...current,
      scale: Math.min(2.4, Math.max(0.55, current.scale * (event.deltaY > 0 ? 0.9 : 1.1))),
    }))
  }
  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    event.currentTarget.setPointerCapture?.(event.pointerId)
    drag.current = { x: event.clientX, y: event.clientY, viewX: view.x, viewY: view.y }
  }
  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    if (!drag.current) return
    setView((current) => ({
      ...current,
      x: drag.current!.viewX + event.clientX - drag.current!.x,
      y: drag.current!.viewY + event.clientY - drag.current!.y,
    }))
  }

  return (
    <div className="dependencyBundle" aria-label="Radial dependency bundle">
      <div className="bundleControls" role="group" aria-label="Bundle zoom and fit controls">
        <button
          type="button"
          aria-label="Zoom bundle in"
          onClick={() =>
            setView((current) => ({ ...current, scale: Math.min(2.4, current.scale * 1.2) }))
          }
        >
          +
        </button>
        <button
          type="button"
          aria-label="Zoom bundle out"
          onClick={() =>
            setView((current) => ({ ...current, scale: Math.max(0.55, current.scale / 1.2) }))
          }
        >
          −
        </button>
        <button type="button" onClick={() => setView({ x: 0, y: 0, scale: 1 })}>
          Fit bundle
        </button>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`${files.length} persisted files and ${edges.length} directed dependency relationships in a radial bundle`}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={() => {
          drag.current = undefined
        }}
      >
        <defs>
          <marker
            id="bundle-arrow-out"
            viewBox="0 0 6 6"
            refX="5"
            refY="3"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" />
          </marker>
          <marker
            id="bundle-arrow-in"
            viewBox="0 0 6 6"
            refX="5"
            refY="3"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" />
          </marker>
        </defs>
        <g
          transform={`translate(${WIDTH / 2 + view.x} ${HEIGHT / 2 + view.y}) scale(${view.scale})`}
        >
          <g className="bundleSectors" aria-hidden="true">
            {sectors.map((sector) => (
              <path key={sector.name} d={sector.path} fill={sector.color} />
            ))}
          </g>
          <g className="bundleEdges" aria-hidden="true">
            {edgePaths.map(({ edge, path }) => {
              const outgoing = activeId === edge.source_repository_file_id
              const incoming = activeId === edge.target_repository_file_id
              const related = !activeId || outgoing || incoming
              return (
                <path
                  key={edge.id}
                  d={path}
                  data-relationship={edge.relationship_type}
                  className={`${related ? '' : 'bundleFaded'} ${outgoing ? 'bundleOutgoing' : ''} ${incoming ? 'bundleIncoming' : ''}`}
                  markerEnd={
                    outgoing
                      ? 'url(#bundle-arrow-out)'
                      : incoming
                        ? 'url(#bundle-arrow-in)'
                        : undefined
                  }
                />
              )
            })}
          </g>
          <g className="bundleFiles">
            {layout.leaves.map((node) => {
              const file = node.data.file!
              const angle = (node.x * 180) / Math.PI
              const left = angle >= 180
              const active = file.repository_file_id === activeId
              const outgoing = outgoingIds.has(file.repository_file_id)
              const incoming = incomingIds.has(file.repository_file_id)
              const related = !activeId || active || outgoing || incoming
              const showLabel =
                files.length <= 44 ||
                file.total_dependency_count > 1 ||
                file.is_entry_point ||
                related
              const color = colorFor(
                colorMode === 'language' ? file.language : topFolder(file.path),
              )
              const size = Math.min(6.5, Math.max(2.8, 2.8 + file.total_dependency_count * 0.42))
              return (
                <g
                  key={file.repository_file_id}
                  role="button"
                  tabIndex={0}
                  aria-label={`${file.path}, ${file.total_dependency_count} dependencies${file.is_entry_point ? ', probable entry point' : ''}`}
                  className={`${active ? 'bundleFileSelected' : ''} ${outgoing ? 'bundleFileOutgoing' : ''} ${incoming ? 'bundleFileIncoming' : ''} ${related ? '' : 'bundleFaded'}`}
                  transform={`rotate(${angle - 90}) translate(${node.y} 0)`}
                  onMouseEnter={() => setHoveredId(file.repository_file_id)}
                  onMouseLeave={() => setHoveredId(undefined)}
                  onFocus={() => setHoveredId(file.repository_file_id)}
                  onBlur={() => setHoveredId(undefined)}
                  onClick={(event) => {
                    event.stopPropagation()
                    onSelect(file)
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onSelect(file)
                    }
                  }}
                >
                  <title>
                    {file.path} · {file.language} · {file.total_dependency_count} relationships
                  </title>
                  {file.is_entry_point && (
                    <path
                      className="bundleEntryMarker"
                      d="M-7,-9 L0,-15 L7,-9"
                      fill="none"
                      stroke={color}
                    />
                  )}
                  <circle r={size} fill={color} />
                  {showLabel && (
                    <text
                      x={left ? -10 : 10}
                      dy="0.32em"
                      textAnchor={left ? 'end' : 'start'}
                      transform={left ? 'rotate(180)' : undefined}
                      fill={color}
                    >
                      {shortName(file.path)}
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        </g>
      </svg>
    </div>
  )
}
