import { request } from './client'
import type {
  Analysis,
  AnalysisSummary,
  CodeFindingsResponse,
  FindingCategory,
  FindingSeverity,
  SuggestedFix,
} from './types'
export const getAnalysis = (id: string) => request<Analysis>(`/analyses/${id}`)
export const getAnalysisSummary = (id: string) =>
  request<AnalysisSummary>(`/analyses/${id}/summary`)
export const getCodeFindings = (
  id: string,
  filters: { severity?: FindingSeverity; category?: FindingCategory },
) => {
  const params = new URLSearchParams({ limit: '100' })
  if (filters.severity) params.set('severity', filters.severity)
  if (filters.category) params.set('category', filters.category)
  return request<CodeFindingsResponse>(`/analyses/${id}/findings?${params}`)
}
export const generateSuggestedFix = (analysisId: string, findingId: string) =>
  request<SuggestedFix>(`/analyses/${analysisId}/findings/${findingId}/suggested-fix`, {
    method: 'POST',
  })
