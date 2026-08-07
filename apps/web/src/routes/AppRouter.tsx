import { createBrowserRouter, RouterProvider } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { AnalysisProgressPage } from '../pages/AnalysisProgressPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RepositoryDashboardPage } from '../pages/RepositoryDashboardPage'
import { RepositoryQuestionPage } from '../pages/RepositoryQuestionPage'
import { RepositorySubmitPage } from '../pages/RepositorySubmitPage'
const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <RepositorySubmitPage /> },
      { path: '/analyses/:analysisId', element: <AnalysisProgressPage /> },
      { path: '/repositories/:repositoryId', element: <RepositoryDashboardPage /> },
      { path: '/analyses/:analysisId/ask', element: <RepositoryQuestionPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
export function AppRouter() {
  return <RouterProvider router={router} />
}
