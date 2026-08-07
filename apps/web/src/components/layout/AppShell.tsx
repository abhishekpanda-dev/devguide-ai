import { NavLink, Outlet, useParams } from 'react-router'

export function AppShell() {
  const { repositoryId, analysisId } = useParams()
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
          </nav>
        </div>
      </header>
      <main id="main-content" className="page">
        <Outlet />
      </main>
    </>
  )
}
