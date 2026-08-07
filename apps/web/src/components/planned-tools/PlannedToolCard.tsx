import type { PlannedTool } from './plannedTools'
import { ComingSoonTooltip } from './ComingSoonTooltip'

export function PlannedToolCard({
  tool,
  onSelect,
}: {
  tool: PlannedTool
  onSelect: (tool: PlannedTool) => void
}) {
  return (
    <ComingSoonTooltip>
      <button
        type="button"
        className={`plannedToolCard plannedToolCard-${tool.accent}`}
        onClick={() => onSelect(tool)}
        aria-label={`${tool.name}, Coming soon`}
      >
        <span className="plannedToolCardTop">
          <strong>{tool.name}</strong>
          <span className="comingSoonBadge">Coming soon</span>
        </span>
        <span>{tool.summary}</span>
      </button>
    </ComingSoonTooltip>
  )
}
