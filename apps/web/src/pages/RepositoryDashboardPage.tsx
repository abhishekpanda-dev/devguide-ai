import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, useSearchParams } from 'react-router'
import {
  getAnalysisSummary,
  getCodeFindings,
  getRepositoryQuality,
  getRepositoryStructure,
} from '../api/analyses'
import { getRepository, getRepositoryAnalyses } from '../api/repositories'
import { ActionsPanel } from '../components/dashboard/ActionsPanel'
import { DashboardToolbar } from '../components/dashboard/DashboardToolbar'
import { DashboardWorkspace } from '../components/dashboard/DashboardWorkspace'
import { RepositorySidebar } from '../components/dashboard/RepositorySidebar'
import { ApiErrorMessage } from '../components/feedback/ApiErrorMessage'

export function RepositoryDashboardPage() {
  const { repositoryId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const client = useQueryClient()
  const [leftOpen, setLeftOpen] = useState(false)
  const [rightOpen, setRightOpen] = useState(false)
  const repository = useQuery({
    queryKey: ['repository', repositoryId],
    queryFn: () => getRepository(repositoryId),
  })
  const analyses = useQuery({
    queryKey: ['repository-analyses', repositoryId],
    queryFn: () => getRepositoryAnalyses(repositoryId),
  })
  const requestedAnalysisId = searchParams.get('analysis')
  const activeAnalysis = requestedAnalysisId
    ? analyses.data?.items.find((item) => item.id === requestedAnalysisId)
    : analyses.data?.items[0]
  const enabled = Boolean(activeAnalysis?.id)
  const summary = useQuery({
    queryKey: ['analysis-summary', activeAnalysis?.id],
    queryFn: () => getAnalysisSummary(activeAnalysis?.id ?? ''),
    enabled,
  })
  const findings = useQuery({
    queryKey: ['code-findings', activeAnalysis?.id, 'dashboard'],
    queryFn: () => getCodeFindings(activeAnalysis?.id ?? '', {}),
    enabled,
  })
  const structure = useQuery({
    queryKey: ['repository-structure', activeAnalysis?.id, 'dashboard'],
    queryFn: () => getRepositoryStructure(activeAnalysis?.id ?? '', {}),
    enabled,
  })
  const quality = useQuery({
    queryKey: ['repository-quality', activeAnalysis?.id],
    queryFn: () => getRepositoryQuality(activeAnalysis?.id ?? ''),
    enabled,
  })

  if (repository.isPending || analyses.isPending)
    return (
      <div className="dashboardLoading" role="status">
        <span className="spinner" />
        Loading intelligence workspaceâ€¦
      </div>
    )
  if (repository.isError)
    return (
      <div className="narrow dashboardFatal">
        <h1>Repository unavailable</h1>
        <ApiErrorMessage error={repository.error} />
      </div>
    )
  if (analyses.isError)
    return (
      <div className="narrow dashboardFatal">
        <h1>{repository.data.name}</h1>
        <ApiErrorMessage error={analyses.error} fallback="Analysis history could not be loaded." />
      </div>
    )
  if (!activeAnalysis)
    return (
      <div className="dashboardEmpty">
        <p className="eyebrow">Repository intelligence</p>
        <h1>{repository.data.name}</h1>
        <p>No completed or queued analysis is available for this repository.</p>
        <a className="button" href="/">
          Analyze a repository
        </a>
      </div>
    )

  const refresh = () =>
    client.invalidateQueries({
      predicate: (query) =>
        query.queryKey.includes(activeAnalysis.id) || query.queryKey.includes(repositoryId),
    })
  return (
    <div className="intelligenceShell" data-testid="dark-dashboard-shell">
      <DashboardToolbar
        repository={repository.data}
        analysis={activeAnalysis}
        onRefresh={refresh}
      />
      <div className="mobilePanelControls">
        <button
          type="button"
          aria-expanded={leftOpen}
          onClick={() => setLeftOpen((value) => !value)}
        >
          Repository summary
        </button>
        <button
          type="button"
          aria-expanded={rightOpen}
          onClick={() => setRightOpen((value) => !value)}
        >
          Findings & actions
        </button>
      </div>
      <div className="dashboardGrid">
        <div className={`dashboardPanelSlot ${leftOpen ? 'mobilePanelOpen' : ''}`}>
          <RepositorySidebar
            analysis={activeAnalysis}
            summary={summary.data}
            findings={findings.data}
            structure={structure.data}
            quality={quality.data}
          />
        </div>
        <DashboardWorkspace
          repository={repository.data}
          analysis={activeAnalysis}
          summary={summary.data}
          structure={structure.data}
          findings={findings.data}
          summaryError={summary.error}
          structureError={structure.error}
        />
        <div className={`dashboardPanelSlot ${rightOpen ? 'mobilePanelOpen' : ''}`}>
          <ActionsPanel
            analysis={activeAnalysis}
            findings={findings.data}
            quality={quality.data}
            structure={structure.data}
            findingsError={findings.error}
            qualityError={quality.error}
          />
        </div>
      </div>
    </div>
  )
}
