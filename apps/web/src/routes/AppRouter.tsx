import { createBrowserRouter, RouterProvider } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { AnalysisProgressPage } from '../pages/AnalysisProgressPage'
import { CodeFindingsPage } from '../pages/CodeFindingsPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RepositoryDashboardPage } from '../pages/RepositoryDashboardPage'
import { RepositoryQuestionPage } from '../pages/RepositoryQuestionPage'
import { RepositorySubmitPage } from '../pages/RepositorySubmitPage'
import { RepositoryStructurePage } from '../pages/RepositoryStructurePage'
import { RepositoryQualityPage } from '../pages/RepositoryQualityPage'
const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <RepositorySubmitPage /> },
      { path: '/analyses/:analysisId', element: <AnalysisProgressPage /> },
      { path: '/repositories/:repositoryId', element: <RepositoryDashboardPage /> },
      { path: '/analyses/:analysisId/ask', element: <RepositoryQuestionPage /> },
      { path: '/analyses/:analysisId/findings', element: <CodeFindingsPage /> },
      { path: '/analyses/:analysisId/structure', element: <RepositoryStructurePage /> },
      { path: '/analyses/:analysisId/quality', element: <RepositoryQualityPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
export function AppRouter() {
  return <RouterProvider router={router} />
}
