import { NavLink, Outlet, useParams } from 'react-router'
import { useAuth } from '../../auth/AuthContext'

export function AppShell() {
  const { repositoryId, analysisId } = useParams()
  const { signOut } = useAuth()
  return (
    <>
      <header className="appHeader">
        <div className="headerInner">
          <NavLink to="/" className="brand" aria-label="DevGuide AI home">
            <span className="brandMark" aria-hidden="true">
              D
            </span>
            DevGuide AI
          </NavLink>
          <nav aria-label="Primary navigation">
            <NavLink to="/">Submit repository</NavLink>
            {repositoryId && <NavLink to={`/repositories/${repositoryId}`}>Repository</NavLink>}
            {analysisId && <NavLink to={`/analyses/${analysisId}/ask`}>Ask DevGuide</NavLink>}
            {analysisId && <NavLink to={`/analyses/${analysisId}/findings`}>Findings</NavLink>}
            {analysisId && <NavLink to={`/analyses/${analysisId}/structure`}>Structure</NavLink>}
            {analysisId && <NavLink to={`/analyses/${analysisId}/quality`}>Quality</NavLink>}
          </nav>
          <button className="headerLogout" type="button" onClick={() => void signOut()}>
            Sign out
          </button>
        </div>
      </header>
      <main id="main-content" className={repositoryId ? 'page dashboardPage' : 'page'}>
        <Outlet />
      </main>
    </>
  )
}
