import { render, screen } from '@testing-library/react'
import { TestOutputPreview } from './TestOutputPreview'

test('renders safe success and failure authentication states', () => {
  const view = render(<TestOutputPreview emailReady passwordReady state="success" />)
  expect(screen.getByText(/Authentication accepted/)).toBeInTheDocument()
  expect(screen.getByText(/Session established/)).toBeInTheDocument()
  expect(screen.getByText(/User profile loaded/)).toBeInTheDocument()
  view.rerender(<TestOutputPreview emailReady passwordReady state="failure" />)
  expect(screen.getByText(/Authentication rejected/)).toBeInTheDocument()
  expect(screen.getByText(/Session not established/)).toBeInTheDocument()
  expect(screen.getByText(/not automated test output/i)).toBeInTheDocument()
})
