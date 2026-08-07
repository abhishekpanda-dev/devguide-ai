import { request } from './client'
import type { Analysis } from './types'
export const getAnalysis = (id: string) => request<Analysis>(`/analyses/${id}`)
