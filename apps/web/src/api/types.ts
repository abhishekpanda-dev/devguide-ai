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
export interface SuggestedFix {
  analysis_job_id: string
  finding_id: string
  rule_id: string
  explanation: string
  probable_fix: string
  example_code: string | null
  citations: Array<{
    path: string
    start_line: number
    end_line: number
    content_hash: string
    source_url: string
  }>
  provider: string
  model: string
  limitations: string[]
  correlation_id: string | null
}
export interface StructureFile {
  repository_file_id: string
  path: string
  language: string
  classification: string
  line_count: number
  content_hash: string
  commit_sha: string
  is_entry_point: boolean
  entry_point_reason: string | null
  entry_point_confidence: number
  inbound_dependency_count: number
  outbound_dependency_count: number
  total_dependency_count: number
}
export interface StructureEdge {
  id: string
  source_repository_file_id: string
  target_repository_file_id: string
  relationship_type: 'imports' | 'requires' | 'reexports'
  module_name: string
  source_path: string
  target_path: string
  source_line: number
  confidence: number
  source_url: string
}
export interface StructureResponse {
  analysis_job_id: string
  repository: { id: string; owner: string; name: string; commit_sha: string }
  files: StructureFile[]
  dependency_edges: StructureEdge[]
  entry_points: StructureFile[]
  summary: {
    file_count: number
    directory_count: number
    language_counts: Record<string, number>
    edge_count: number
    entry_point_count: number
    highest_inbound_files: StructureFile[]
    highest_outbound_files: StructureFile[]
    most_connected_files: StructureFile[]
  }
  limitations: string[]
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
export interface QualityResponse {
  analysis_job_id: string
  overall_score: number
  category_scores: Record<string, number>
  score_breakdown: Array<{
    category: string
    signal_type: string
    count: number
    points_deducted: number
    explanation: string
  }>
  unused_code_candidates: Array<{
    id: string
    symbol_name: string
    symbol_kind: string
    path: string
    language: string
    start_line: number
    end_line: number
    reason: string
    confidence: number
    recommendation: string
    excerpt: string
    source_url: string
  }>
  duplicate_code_groups: Array<{
    group_id: string
    match_type: string
    confidence: number
    recommendation: string
    members: Array<{
      path: string
      language: string
      start_line: number
      end_line: number
      excerpt: string
      source_url: string
    }>
  }>
  summary: { unused_candidate_count: number; duplicate_group_count: number }
  limitations: string[]
  score_version: string
}
