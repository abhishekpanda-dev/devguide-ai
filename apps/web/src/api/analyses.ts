import { request } from './client'
import type { Analysis, AnalysisSummary } from './types'
export const getAnalysis = (id: string) => request<Analysis>(`/analyses/${id}`)
export const getAnalysisSummary = (id: string) =>
  request<AnalysisSummary>(`/analyses/${id}/summary`)
