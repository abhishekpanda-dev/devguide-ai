import { request } from './client'
import type { QuestionRequest, QuestionResponse } from './types'
export const askQuestion = (id: string, body: QuestionRequest) =>
  request<QuestionResponse>(`/analyses/${id}/questions`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
