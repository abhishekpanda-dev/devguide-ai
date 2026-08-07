import { useCallback, useRef, useState } from 'react'
import { ComingSoonTooltip } from './ComingSoonTooltip'
import { PlannedToolDialog } from './PlannedToolDialog'

export function PlannedToolsLauncher() {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const close = useCallback(() => {
    setOpen(false)
    requestAnimationFrame(() => triggerRef.current?.focus())
  }, [])
  return (
    <>
      <ComingSoonTooltip>
        <button
          ref={triggerRef}
          type="button"
          className="toolsLauncherButton"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          Tools <span>Planned</span>
        </button>
      </ComingSoonTooltip>
      <PlannedToolDialog open={open} onClose={close} />
    </>
  )
}
