import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PlannedToolsLauncher } from './PlannedToolsLauncher'
import { plannedTools } from './plannedTools'

function renderLauncher() {
  return render(
    <main className="intelligenceShell">
      <a href="/existing">Existing dashboard action</a>
      <PlannedToolsLauncher />
    </main>,
  )
}

test('renders a compact launcher and exposes Coming soon on hover and focus', async () => {
  const user = userEvent.setup()
  renderLauncher()
  const launcher = screen.getByRole('button', { name: /Tools/ })
  expect(launcher).toHaveAttribute('aria-haspopup', 'dialog')
  await user.hover(launcher)
  expect(screen.getByRole('tooltip', { name: 'Coming soon' })).toBeInTheDocument()
  launcher.focus()
  expect(launcher).toHaveFocus()
})

test('shows all data-driven planned tools and makes the dashboard inert', async () => {
  const user = userEvent.setup()
  const { container } = renderLauncher()
  await user.click(screen.getByRole('button', { name: /Tools/ }))
  expect(screen.getByRole('dialog', { name: 'Tools' })).toBeInTheDocument()
  for (const tool of plannedTools) {
    expect(screen.getByRole('button', { name: `${tool.name}, Coming soon` })).toBeInTheDocument()
  }
  expect(container.querySelector('.intelligenceShell')).toHaveAttribute('inert')
  expect(screen.getByRole('button', { name: 'Close planned tools' })).toHaveFocus()
})

test('opens accurate concept details without fake results or network requests', async () => {
  const user = userEvent.setup()
  const fetchSpy = vi.spyOn(globalThis, 'fetch')
  renderLauncher()
  await user.click(screen.getByRole('button', { name: /Tools/ }))
  await user.click(screen.getByRole('button', { name: 'Secret Scanner, Coming soon' }))
  expect(screen.getByRole('heading', { name: 'Secret Scanner' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Planned capabilities' })).toBeInTheDocument()
  expect(screen.getByText('Redact detected values')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Expected inputs' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Expected outputs' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Why it will be useful' })).toBeInTheDocument()
  expect(
    screen.getByText(/not implemented yet.*No scan, analysis, or repository modification/s),
  ).toBeInTheDocument()
  expect(
    screen.queryByText(/vulnerabilities found|scan complete|health score|progress/i),
  ).not.toBeInTheDocument()
  expect(fetchSpy).not.toHaveBeenCalled()
})

test('supports Back to tools, Close, Escape, and focus restoration', async () => {
  const user = userEvent.setup()
  renderLauncher()
  const launcher = screen.getByRole('button', { name: /Tools/ })
  await user.click(launcher)
  await user.click(screen.getByRole('button', { name: 'Complexity Analysis, Coming soon' }))
  await user.click(screen.getByRole('button', { name: 'Back to tools' }))
  expect(screen.getByRole('heading', { name: 'Tools' })).toBeInTheDocument()
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await waitFor(() => expect(launcher).toHaveFocus())
  await user.click(launcher)
  await user.click(screen.getByRole('button', { name: 'Close planned tools' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await waitFor(() => expect(launcher).toHaveFocus())
})

test('supports keyboard navigation and searchable one-dialog content', async () => {
  const user = userEvent.setup()
  renderLauncher()
  const launcher = screen.getByRole('button', { name: /Tools/ })
  launcher.focus()
  await user.keyboard('{Enter}')
  await user.tab()
  expect(screen.getByLabelText('Search planned tools')).toHaveFocus()
  await user.type(screen.getByLabelText('Search planned tools'), 'coverage')
  expect(
    screen.getByRole('button', { name: 'Test Coverage Intelligence, Coming soon' }),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Security Scanner, Coming soon' }),
  ).not.toBeInTheDocument()
})
