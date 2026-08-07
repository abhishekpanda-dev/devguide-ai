import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { PlannedToolCard } from './PlannedToolCard'
import { plannedToolCategories, plannedTools, type PlannedTool } from './plannedTools'

const NOTICE =
  'This capability is planned and is not implemented yet. No scan, analysis, or repository modification has been performed.'

export function PlannedToolDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [selected, setSelected] = useState<PlannedTool>()
  const [search, setSearch] = useState('')
  const closeRef = useRef<HTMLButtonElement>(null)
  const matches = useMemo(() => {
    const query = search.trim().toLowerCase()
    return query
      ? plannedTools.filter((tool) =>
          `${tool.name} ${tool.category} ${tool.summary}`.toLowerCase().includes(query),
        )
      : plannedTools
  }, [search])
  useEffect(() => {
    if (!open) return
    const shell = document.querySelector<HTMLElement>('.intelligenceShell')
    shell?.setAttribute('inert', '')
    closeRef.current?.focus()
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
    }
    document.addEventListener('keydown', escape)
    return () => {
      shell?.removeAttribute('inert')
      document.removeEventListener('keydown', escape)
    }
  }, [onClose, open])
  useEffect(() => {
    if (!open) {
      setSelected(undefined)
      setSearch('')
    }
  }, [open])
  if (!open) return null
  return createPortal(
    <div className="plannedToolsBackdrop">
      <section
        className="plannedToolsDialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="planned-tools-title"
      >
        <header className="plannedToolsDialogHeader">
          <div>
            <p className="eyebrow">Future capabilities</p>
            <h2 id="planned-tools-title">{selected?.name ?? 'Tools'}</h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="plannedToolsClose"
            onClick={onClose}
            aria-label="Close planned tools"
          >
            Close
          </button>
        </header>
        {selected ? (
          <div className="plannedToolDetail">
            <span className="comingSoonBadge">Coming soon</span>
            <p className="plannedToolSummary">{selected.summary}</p>
            <section>
              <h3>Planned capabilities</h3>
              <ul>
                {selected.capabilities.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
            <div className="plannedToolDetailColumns">
              <section>
                <h3>Expected inputs</h3>
                <ul>
                  {selected.expectedInputs.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>Expected outputs</h3>
                <ul>
                  {selected.expectedOutputs.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            </div>
            <section>
              <h3>Why it will be useful</h3>
              <p>{selected.usefulness}</p>
            </section>
            <p className="plannedToolNotice">{NOTICE}</p>
            <button
              type="button"
              className="plannedToolsBack"
              onClick={() => setSelected(undefined)}
            >
              Back to tools
            </button>
          </div>
        ) : (
          <div className="plannedToolsMenu">
            <label className="plannedToolsSearch">
              Search planned tools
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Security, testing, reporting…"
              />
            </label>
            {plannedToolCategories.map((category) => {
              const tools = matches.filter((tool) => tool.category === category)
              return tools.length ? (
                <section
                  key={category}
                  aria-labelledby={`planned-${category.replace(' ', '-').toLowerCase()}`}
                >
                  <h3 id={`planned-${category.replace(' ', '-').toLowerCase()}`}>{category}</h3>
                  <div className="plannedToolsGrid">
                    {tools.map((tool) => (
                      <PlannedToolCard key={tool.id} tool={tool} onSelect={setSelected} />
                    ))}
                  </div>
                </section>
              ) : null
            })}
            {!matches.length && <p className="emptyCompact">No planned tools match that search.</p>}
          </div>
        )}
      </section>
    </div>,
    document.body,
  )
}
