import type { ReactNode } from 'react'

export function ComingSoonTooltip({ children }: { children: ReactNode }) {
  return (
    <span className="comingSoonTooltip">
      <span role="tooltip">Coming soon</span>
      {children}
    </span>
  )
}
