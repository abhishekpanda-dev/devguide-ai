import { Link } from 'react-router'
export function NotFoundPage() {
  return (
    <div className="narrow state">
      <p className="eyebrow">404</p>
      <h1>Page not found</h1>
      <p>The requested DevGuide page does not exist.</p>
      <Link className="button" to="/">
        Submit a repository
      </Link>
    </div>
  )
}
