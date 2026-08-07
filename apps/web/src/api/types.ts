export type RepositoryStatus = 'pending' | 'ready' | 'failed' | 'archived'
export type AnalysisStatus = 'queued' | 'running' | 'partial' | 'completed' | 'failed' | 'cancelled'

export interface Repository {
  id: string
  source_type: 'github_public'
  source_url: string
  normalized_url: string
  owner: string
  name: string
  default_branch: string | null
  latest_commit_sha: string | null
  status: RepositoryStatus
  created_at: string
  updated_at: string
}

export interface Analysis {
  id: string
  repository_id: string
  status: AnalysisStatus
  current_stage: string | null
  progress_percent: number
  pipeline_version: string
  error_code: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface SubmissionResponse {
  repository: Repository
  analysis_job: Analysis
}
export interface AnalysisList {
  items: Analysis[]
  limit: number
  offset: number
}
export interface AnalysisLanguageSummary {
  language: string
  file_count: number
  line_count: number
}
export interface AnalysisSummary {
  analysis_job_id: string
  files_analyzed: number
  chunks_created: number
  languages: AnalysisLanguageSummary[]
  total_lines: number
  test_file_count: number
  documentation_file_count: number
  skipped_file_count: number
  limitations: string[]
}
export type FindingSeverity = 'info' | 'warning' | 'high'
export type FindingCategory = 'maintainability' | 'reliability' | 'security'
export interface CodeFinding {
  id: string
  rule_id: string
  severity: FindingSeverity
  category: FindingCategory
  title: string
  explanation: string
  path: string
  start_line: number
  end_line: number
  evidence_excerpt: string
  deterministic_recommendation: string
  confidence: number
  content_hash: string
  commit_sha: string
  source_url: string
}
export interface CodeFindingsResponse {
  analysis_job_id: string
  total_count: number
  returned_count: number
  findings: CodeFinding[]
  limitations: string[]
  severity_counts: Record<FindingSeverity, number>
}
export interface Citation {
  chunk_id: string
  repository_file_id: string
  path: string
  start_line: number
  end_line: number
  content_hash: string
}
export interface QuestionRequest {
  question: string
  language_filters?: string[]
  path_prefix?: string
  retrieval_limit?: number
  retrieval_minimum_score?: number
  maximum_citations?: number
}
export interface QuestionResponse {
  analysis_job_id: string
  question: string
  answer: string
  citations: Citation[]
  insufficient_evidence: boolean
  evidence_quality: 'high' | 'medium' | 'low' | 'insufficient'
  retrieved_evidence_count: number
  provider: string | null
  model: string | null
  limitations: string[]
  correlation_id: string | null
}
