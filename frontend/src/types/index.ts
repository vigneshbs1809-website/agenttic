export interface Document {
  id: string;
  project_id?: string;
  title: string;
  authors: string[];
  publication_year?: number;
  abstract?: string;
  filename: string;
  file_size_bytes: number;
  total_pages?: number;
  processed_status: 'pending' | 'processing' | 'completed' | 'failed' | 'metadata_only' | string;
  created_at: string;
  updated_at: string;
  chunk_count: number;
  doi?: string;
}

export interface Citation {
  document_id: string;
  document_title: string;
  chunk_index: number;
  snippet: string;
  similarity_score: number;
}

export interface RAGResponse {
  query: string;
  answer: string;
  citations: Citation[];
  duration_ms: number;
  model_used: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  degree?: number;
  centrality?: number;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface SystemHealth {
  status: string;
  ollama_connected: boolean;
  ollama_model: string;
  embed_model: string;
  ram_used_mb: number;
  ram_total_mb: number;
  ram_percent: number;
  database_connected: boolean;
  total_documents: number;
  total_chunks: number;
}

export interface RecentActivityItem {
  id: string;
  type: string;
  action: string;
  title: string;
  project_id?: string | null;
  timestamp?: string;
  status?: string;
  badge?: string;
}

export interface AnalyticsSummary {
  total_projects?: number;
  total_documents: number;
  total_uploaded_papers?: number;
  processed_papers?: number;
  total_chunks: number;
  avg_pages: number;
  total_queries: number;
  total_gaps?: number;
  identified_research_gaps?: number;
  total_verifications?: number;
  verified_claims?: number;
  year_distribution: { year: string; papers: number }[];
  status_distribution: { status: string; count: number }[];
  recent_activity?: RecentActivityItem[];
}

export interface GapEvidenceItem {
  id?: string;
  paper_id: string;
  paper_title: string;
  section_name?: string;
  section_title?: string;
  page_number?: number;
  original_text?: string;
  quote_or_excerpt?: string;
  is_counter_evidence: boolean;
  confidence?: number;
}

export interface ResearchGapItem {
  id: string;
  project_id: string;
  title: string;
  category: string;
  description: string;
  identification_method: string;
  suggested_direction?: string;
  confidence_score: number;
  confidence_justification?: string;
  supporting_paper_count: number;
  status: string;
  evidence: GapEvidenceItem[];
  created_at: string;
}

export interface VerificationResultItem {
  id?: string;
  paper_id?: string;
  paper_title?: string;
  source_paper?: { paper_id: string; title: string };
  claim_text: string;
  page_number?: number;
  section_title?: string;
  verification_status: 'Supported' | 'Partially Supported' | 'Contradicted' | 'Insufficient Evidence' | string;
  explanation: string;
  original_evidence?: string;
  supporting_evidence?: string;
  counter_evidence?: string;
  is_verified_finding: boolean;
  confidence_score?: number;
  similarity_score?: number;
  created_at?: string;
}

export interface ResearchProjectItem {
  id: string;
  title: string;
  description?: string;
  domain?: string;
  status: string;
  created_at: string;
  paper_count?: number;
}

export interface WorkflowStageInfo {
  stage_id: string;
  stage_name: string;
  agent_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  message: string;
  duration_ms: number;
  retry_count: number;
  input_summary?: string;
  output_summary?: string;
  error_message?: string;
  completed_at?: string;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  project_id: string;
  topic?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  current_stage?: string;
  completed_stages: number;
  total_stages: number;
  progress_percent: number;
  stages: WorkflowStageInfo[];
  logs: string[];
  final_report_id?: string;
  final_report_markdown?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunRequest {
  project_id?: string;
  project_title?: string;
  topic?: string;
  keywords?: string[];
  paper_ids?: string[];
  skip_stages?: string[];
  force_restart?: boolean;
}

export interface WorkflowHistoryItem {
  workflow_id: string;
  project_id: string;
  topic?: string;
  status: string;
  completed_stages: number;
  total_stages: number;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Contradiction Detection Types
// ---------------------------------------------------------------------------
export type ContradictionCategory =
  | 'experimental_results'
  | 'conclusions'
  | 'methodology'
  | 'dataset_findings'
  | 'algorithmic_claims';

export type ContradictionNature =
  | 'genuine_contradiction'
  | 'condition_dependent_difference'
  | 'methodological_divergence';

export interface ContradictionItem {
  id: string;
  project_id?: string;
  paper_a_id: string;
  paper_b_id: string;
  paper_a_title: string;
  paper_b_title: string;
  category: ContradictionCategory;
  nature: ContradictionNature;
  title: string;
  description: string;
  passage_a: string;
  passage_b: string;
  page_a?: number;
  page_b?: number;
  section_a?: string;
  section_b?: string;
  root_cause_analysis?: string;
  severity: 'high' | 'medium' | 'low';
  confidence_score: number;
  status: string;
  created_at: string;
}

export interface DetectContradictionsResponse {
  total_contradictions: number;
  genuine_count: number;
  condition_dependent_count: number;
  methodological_divergence_count: number;
  category_breakdown: Record<string, number>;
  contradictions: ContradictionItem[];
}

export interface DetectContradictionsRequest {
  project_id?: string;
  paper_ids?: string[];
  categories?: ContradictionCategory[];
  force_redetect?: boolean;
}

// ---------------------------------------------------------------------------
// Research Trend Analysis Types
// ---------------------------------------------------------------------------
export interface YearTrend {
  year: number;
  paper_count: number;
  cumulative_papers: number;
}

export interface AlgorithmTrend {
  name: string;
  count: number;
  papers: string[];
  percentage: number;
}

export interface DatasetTrend {
  name: string;
  count: number;
  papers: string[];
  percentage: number;
}

export interface TopicTrend {
  topic: string;
  count: number;
  percentage: number;
}

export interface LimitationTrend {
  limitation: string;
  count: number;
  papers: string[];
  category?: string;
}

export interface EmergingDirectionTrend {
  direction: string;
  mention_count: number;
  recency_score: number;
  suggested_by: string[];
}

export interface UnderexploredArea {
  area: string;
  gap_category: string;
  reason: string;
  identified_in_gaps: number;
  evaluated_in_papers: number;
}

export interface ResearchTrendsResponse {
  project_id?: string;
  total_papers_analyzed: number;
  total_analyses_analyzed: number;
  total_gaps_analyzed: number;
  publications_by_year: YearTrend[];
  top_algorithms: AlgorithmTrend[];
  top_datasets: DatasetTrend[];
  topic_distribution: TopicTrend[];
  common_limitations: LimitationTrend[];
  emerging_directions: EmergingDirectionTrend[];
  underexplored_areas: UnderexploredArea[];
  analysis_timestamp: string;
}

// ---------------------------------------------------------------------------
// Paper Discovery Types
// ---------------------------------------------------------------------------
export interface DiscoveredPaperItem {
  id?: string;
  title: string;
  abstract?: string;
  authors: string[];
  doi?: string;
  year?: number;
  url?: string;
  primary_url?: string;
  pdf_url?: string;
  venue?: string;
  citation_count?: number;
  is_open_access: boolean;
  sources: string[];
  relevance_score?: number;
}

export interface DiscoverySearchRequest {
  topic: string;
  keywords?: string[];
  year_start?: number;
  year_end?: number;
  author?: string;
  open_access_only?: boolean;
  sources?: string[];
  limit_per_source?: number;
  sort_by?: 'relevance' | 'year_desc' | 'year_asc' | 'citations_desc' | string;
}

export interface DiscoverySearchResponse {
  topic: string;
  total_found: number;
  sources_queried: string[];
  source_statuses: Record<string, string>;
  papers: DiscoveredPaperItem[];
}

export interface AddPaperToProjectRequest {
  project_id: string;
  paper: DiscoveredPaperItem;
  download_pdf?: boolean;
  process_document?: boolean;
}

export interface AddPaperToProjectResponse {
  paper_id: string;
  project_id: string;
  title: string;
  doi?: string;
  pdf_downloaded: boolean;
  processed_status: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Paper Analysis Types
// ---------------------------------------------------------------------------
export interface EvidenceRef {
  quote: string;
  page_number?: number;
  section_name?: string;
  relevance_score?: number;
}

export interface DimensionAnalysis {
  dimension_name: string;
  summary: string;
  findings: string[];
  evidence: EvidenceRef[];
  status?: string;
}

export interface ResearchAnalysisReport {
  paper_id: string;
  paper_title: string;
  authors: string[];
  publication_year?: number;
  doi?: string;
  journal_or_conference?: string;
  abstract?: string;
  executive_summary?: string;

  research_problem?: DimensionAnalysis;
  objectives?: DimensionAnalysis;
  motivation?: DimensionAnalysis;
  methodology?: DimensionAnalysis;
  algorithms?: DimensionAnalysis;
  dataset_characteristics?: DimensionAnalysis;
  data_preprocessing?: DimensionAnalysis;
  experimental_setup?: DimensionAnalysis;
  evaluation_metrics?: DimensionAnalysis;
  results?: DimensionAnalysis;
  strengths?: DimensionAnalysis;
  limitations?: DimensionAnalysis;
  future_directions?: DimensionAnalysis;
  reproducibility?: DimensionAnalysis;

  dimensions?: Record<string, any>;
  report_markdown?: string;
  model_used?: string;
  is_cached?: boolean;
  created_at?: string;
  analyzed_at?: string;
}

// ---------------------------------------------------------------------------
// Comparative Analysis Types
// ---------------------------------------------------------------------------
export interface MatrixCell {
  paper_id: string;
  paper_title: string;
  criterion_name: string;
  value: string;
  evidence_quote?: string;
  page_number?: number;
  section_name?: string;
}

export interface MatrixRow {
  criterion_key: string;
  criterion_label: string;
  cells: MatrixCell[];
}

export interface ComparabilityAssessment {
  is_directly_comparable: boolean;
  verdict: string;
  dataset_comparability: string;
  experimental_setting_comparability: string;
  metric_comparability: string;
  warning_or_caveat: string;
}

export interface CrossPaperComparisonReport {
  comparison_id: string;
  comparison_title?: string;
  title?: string;
  project_id?: string;
  paper_ids?: string[];
  compared_papers?: Array<{ id: string; title: string; year?: number; authors?: string[] }>;
  matrix: MatrixRow[];
  similarities?: any[];
  methodological_differences?: any[];
  dataset_comparison?: any[];
  evaluation_comparison?: any[];
  comparability_assessment?: ComparabilityAssessment;
  contradictory_findings?: any[];
  underexplored_approaches?: any[];
  comparative_summary_markdown?: string;
  comparative_summary?: string;
  model_used?: string;
  created_at: string;
  is_cached?: boolean;
}

// ---------------------------------------------------------------------------
// Generated Reports Types
// ---------------------------------------------------------------------------
export type AcademicReportType = 
  | 'literature_review'
  | 'individual_paper'
  | 'comparative_analysis'
  | 'gap_analysis'
  | 'contradiction_analysis'
  | 'proposed_methodology';

export type CitationStyle = 'IEEE' | 'APA';

export interface ReportGenerateRequest {
  project_id: string;
  report_type: AcademicReportType;
  citation_style: CitationStyle;
  paper_ids?: string[];
  custom_title?: string;
}

export interface ReportSummaryItem {
  id: string;
  project_id: string;
  project_title: string;
  report_title: string;
  report_type: AcademicReportType;
  generation_model: string;
  citation_style: CitationStyle;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface ReportDetailResponse {
  id: string;
  project_id: string;
  project_title: string;
  report_title: string;
  report_type: AcademicReportType;
  content_markdown: string;
  generation_model: string;
  citation_style: CitationStyle;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface GeneratedReportItem {
  id: string;
  project_id: string;
  report_title: string;
  report_type: string;
  content_markdown: string;
  generation_model: string;
  created_at: string;
  updated_at?: string;
}

// ---------------------------------------------------------------------------
// System Settings & Health Telemetry Types
// ---------------------------------------------------------------------------
export interface InstalledOllamaModel {
  name: string;
  model: string;
  size_bytes: number;
  size_mb: number;
  modified_at: string;
  details?: Record<string, any>;
}

export interface CompleteSystemStatus {
  timestamp: number;
  backend: {
    name: string;
    version: string;
    environment: string;
    host: string;
    port: number;
    status: string;
    uptime_seconds: number;
    pid: number;
  };
  system_resources: {
    ram_used_mb: number;
    ram_total_mb: number;
    ram_percent: number;
    is_low_ram_environment: boolean;
    platform: string;
  };
  sqlite: {
    connected: boolean;
    error?: string;
    path: string;
    size_mb: number;
    version: string;
    journal_mode: string;
    synchronous: string;
    counts: {
      projects: number;
      papers: number;
      sections: number;
      gaps: number;
      verifications: number;
      contradictions: number;
      agent_logs: number;
    };
  };
  chromadb: {
    connected: boolean;
    error?: string;
    persist_dir: string;
    size_mb: number;
    active_collection: string;
    total_chunks_indexed: number;
    collections: string[];
    distance_metric: string;
  };
  pdf_storage: {
    dir_path: string;
    exists: boolean;
    total_pdf_files: number;
    total_size_mb: number;
    writable: boolean;
  };
  ollama: {
    connected: boolean;
    base_url: string;
    error?: string;
    installed_models_count: number;
    installed_models: InstalledOllamaModel[];
  };
  selected_llm: {
    model: string;
    context_length: number;
    temperature: number;
    max_output_tokens: number;
    timeout_seconds: number;
    is_ready: boolean;
  };
  embedding_model: {
    model: string;
    dimensions: number;
    is_ready: boolean;
  };
}

export interface DiagnosticCheckItem {
  component: string;
  status: 'pass' | 'warn' | 'fail';
  message: string;
  details?: Record<string, any>;
}

export interface SystemDiagnosticsResponse {
  overall_status: 'healthy' | 'warning' | 'fail';
  timestamp: number;
  total_checks: number;
  passed: number;
  warnings: number;
  failures: number;
  checks: DiagnosticCheckItem[];
}

export interface DatabaseTestResponse {
  status: string;
  sqlite: {
    connected: boolean;
    version?: string;
    paper_records?: number;
    latency_ms: number;
    error?: string;
  };
  chromadb: {
    connected: boolean;
    collection?: string;
    total_chunks?: number;
    latency_ms: number;
    error?: string;
  };
}

export interface SystemConfig {
  chunk_size: number;
  chunk_overlap: number;
  retrieval_top_k: number;
  model_output_limit: number;
  temperature: number;
  context_length: number;
  timeout_seconds: number;
  is_low_ram_optimized: boolean;
}

export interface SystemConfigUpdate {
  chunk_size: number;
  chunk_overlap: number;
  retrieval_top_k: number;
  model_output_limit: number;
  temperature?: number;
}

export interface AgentExecutionLogItem {
  id: string;
  project_id?: string;
  agent_name: string;
  action_type: string;
  input_payload?: string;
  output_summary?: string;
  status: string;
  duration_ms?: number;
  error_message?: string;
  created_at?: string;
}

export interface AgentLogsResponse {
  total_count: number;
  logs: AgentExecutionLogItem[];
}




