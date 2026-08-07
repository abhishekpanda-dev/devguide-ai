import { request } from './client'
import type { AnalysisList, Repository, SubmissionResponse } from './types'
export const submitRepository = (source_url: string) =>
  request<SubmissionResponse>('/repositories', {
    method: 'POST',
    body: JSON.stringify({ source_url }),
  })
export const getRepository = (id: string) => request<Repository>(`/repositories/${id}`)
export const getRepositoryAnalyses = (id: string) =>
  request<AnalysisList>(`/repositories/${id}/analyses?limit=20&offset=0`)
