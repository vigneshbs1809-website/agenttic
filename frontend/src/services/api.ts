import {
  Document,
  RAGResponse,
  GraphData,
  SystemHealth,
  AnalyticsSummary,
  ResearchGapItem,
  VerificationResultItem,
  ResearchProjectItem,
  WorkflowStatusResponse,
  WorkflowRunRequest,
  WorkflowHistoryItem,
  ContradictionItem,
  DetectContradictionsResponse,
  DetectContradictionsRequest,
  ResearchTrendsResponse,
  DiscoveredPaperItem,
  DiscoverySearchRequest,
  DiscoverySearchResponse,
  AddPaperToProjectRequest,
  AddPaperToProjectResponse,
  ResearchAnalysisReport,
  CrossPaperComparisonReport,
  GeneratedReportItem,
  ReportGenerateRequest,
  ReportSummaryItem,
  ReportDetailResponse,
  AcademicReportType,
  CitationStyle,
  CompleteSystemStatus,
  SystemDiagnosticsResponse,
  DatabaseTestResponse,
  SystemConfig,
  SystemConfigUpdate,
  AgentLogsResponse,
  AgentExecutionLogItem,
  InstalledOllamaModel
} from '../types';

const API_BASE = '/api';

export const api = {
  // ---------------------------------------------------------------------------
  // 1. System Health & Diagnostics
  // ---------------------------------------------------------------------------
  getHealth: async (): Promise<SystemHealth> => {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Failed to fetch system health');
    const data = await res.json();
    return {
      status: data.status,
      ollama_connected: Boolean(data.ollama?.connected),
      ollama_model: data.ollama?.llm_model || 'qwen3:1.7b',
      embed_model: data.ollama?.embed_model || 'nomic-embed-text',
      ram_used_mb: data.system_resources?.ram_used_mb || 0,
      ram_total_mb: data.system_resources?.ram_total_mb || 8192,
      ram_percent: data.system_resources?.ram_percent || 0,
      database_connected: Boolean(data.database?.connected),
      total_documents: 0,
      total_chunks: 0,
    };
  },

  testOllama: async (prompt?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/ollama/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt || 'State in one short sentence what scientific research is.' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Ollama test failed' }));
      throw new Error(err.detail || 'Ollama connection test failed');
    }
    return res.json();
  },

  getOllamaModels: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/ollama/models`);
    if (!res.ok) return { count: 0, models: [] };
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 2. Documents Management & Ingestion
  // ---------------------------------------------------------------------------
  getDocuments: async (projectId?: string): Promise<Document[]> => {
    const url = projectId
      ? `${API_BASE}/documents?project_id=${projectId}`
      : `${API_BASE}/documents`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch documents');
    const docs = await res.json();
    return docs.map((d: any) => ({
      ...d,
      chunk_count: d.section_count || 0
    }));
  },

  uploadDocument: async (file: File, projectId?: string): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    const url = projectId
      ? `${API_BASE}/documents/upload?project_id=${projectId}`
      : `${API_BASE}/documents/upload`;
    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Failed to upload document');
    }
    const doc = await res.json();
    return {
      ...doc,
      chunk_count: doc.section_count || 0
    };
  },

  uploadBatchDocuments: async (files: File[], projectId?: string): Promise<{ uploaded_count: number; errors: string[] }> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const url = projectId
      ? `${API_BASE}/documents/batch-upload?project_id=${projectId}`
      : `${API_BASE}/documents/batch-upload`;
    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Batch upload failed' }));
      throw new Error(err.detail || 'Failed to batch upload documents');
    }
    return res.json();
  },

  getDocumentDetails: async (id: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/documents/${id}`);
    if (!res.ok) throw new Error('Failed to fetch document details');
    return res.json();
  },

  getDocumentPages: async (id: string): Promise<Array<{ page_number: number; text: string; character_count: number; token_count: number }>> => {
    const res = await fetch(`${API_BASE}/documents/${id}/pages`);
    if (!res.ok) throw new Error('Failed to fetch document pages');
    return res.json();
  },

  getDocumentSections: async (id: string): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/documents/${id}/sections`);
    if (!res.ok) throw new Error('Failed to fetch document sections');
    return res.json();
  },

  deleteDocument: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/documents/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete document');
  },

  reprocessDocument: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/documents/${id}/reprocess`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to reprocess document');
  },

  // ---------------------------------------------------------------------------
  // 3. Projects
  // ---------------------------------------------------------------------------
  getProjects: async (): Promise<ResearchProjectItem[]> => {
    const res = await fetch(`${API_BASE}/projects`);
    if (!res.ok) return [];
    return res.json();
  },

  createProject: async (data: { title: string; domain?: string; description?: string }): Promise<ResearchProjectItem> => {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create project' }));
      throw new Error(err.detail || 'Failed to create project');
    }
    return res.json();
  },

  updateProject: async (
    projectId: string,
    data: { title?: string; domain?: string; description?: string; status?: string }
  ): Promise<ResearchProjectItem> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to update project' }));
      throw new Error(err.detail || 'Failed to update project');
    }
    return res.json();
  },

  getProjectById: async (projectId: string): Promise<ResearchProjectItem> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`);
    if (!res.ok) throw new Error('Project not found');
    return res.json();
  },

  deleteProject: async (projectId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete project');
  },

  // ---------------------------------------------------------------------------
  // 4. RAG Synthesis
  // ---------------------------------------------------------------------------
  queryLiterature: async (query: string, topK = 4, docFilter?: string[]): Promise<RAGResponse> => {
    const res = await fetch(`${API_BASE}/rag/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: query,
        top_k: topK,
        paper_ids: docFilter && docFilter.length > 0 ? docFilter : null,
        method: 'hybrid',
      }),
    });
    if (!res.ok) throw new Error('Failed to synthesize literature answer');
    const data = await res.json();
    const citations = (data.citations || []).map((c: any, idx: number) => ({
      document_id: c.paper_id,
      document_title: c.paper_title,
      chunk_index: idx,
      snippet: `[Page ${c.page_number} | ${c.section_name}] ${c.original_text}`,
      similarity_score: c.retrieval_score
    }));
    return {
      query: data.question,
      answer: data.answer,
      citations: citations,
      duration_ms: data.duration_ms,
      model_used: data.model_used
    };
  },

  // ---------------------------------------------------------------------------
  // 5. Research Knowledge Graph
  // ---------------------------------------------------------------------------
  getGraphOverview: async (filters?: { algorithm?: string; year?: number; topic?: string }): Promise<GraphData> => {
    const params = new URLSearchParams();
    if (filters?.algorithm) params.append('algorithm', filters.algorithm);
    if (filters?.year) params.append('year', String(filters.year));
    if (filters?.topic) params.append('topic', filters.topic);
    params.append('max_papers', '50');

    const res = await fetch(`${API_BASE}/graph/overview?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch knowledge graph');
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 6. Analytics
  // ---------------------------------------------------------------------------
  getAnalytics: async (): Promise<AnalyticsSummary> => {
    const res = await fetch(`${API_BASE}/analytics/summary`);
    if (!res.ok) throw new Error('Failed to fetch analytics summary');
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 7. Research Gap Discovery Agent
  // ---------------------------------------------------------------------------
  getGapCategories: async (): Promise<string[]> => {
    const res = await fetch(`${API_BASE}/gaps/categories`);
    if (!res.ok) return [];
    return res.json();
  },

  getProjectGaps: async (projectId: string, gapType?: string): Promise<{ total_gaps: number; gaps: ResearchGapItem[] }> => {
    const url = gapType
      ? `${API_BASE}/gaps/project/${projectId}?gap_type=${gapType}`
      : `${API_BASE}/gaps/project/${projectId}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch project research gaps');
    return res.json();
  },

  discoverProjectGaps: async (
    projectId: string,
    options?: { include_explicit?: boolean; include_implicit?: boolean; force_rediscover?: boolean }
  ): Promise<{ total_gaps: number; gaps: ResearchGapItem[] }> => {
    const res = await fetch(`${API_BASE}/gaps/discover/${projectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        include_explicit: options?.include_explicit ?? true,
        include_implicit: options?.include_implicit ?? true,
        force_rediscover: options?.force_rediscover ?? false,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Gap discovery failed' }));
      throw new Error(err.detail || 'Failed to run Research Gap Discovery Agent');
    }
    return res.json();
  },

  getAllGaps: async (params?: {
    projectId?: string;
    gapType?: string;
    method?: string;
    status?: string;
  }): Promise<{ total_gaps: number; gaps: ResearchGapItem[] }> => {
    const searchParams = new URLSearchParams();
    if (params?.projectId && params.projectId !== 'all') searchParams.append('project_id', params.projectId);
    if (params?.gapType && params.gapType !== 'all') searchParams.append('gap_type', params.gapType);
    if (params?.method && params.method !== 'all') searchParams.append('identification_method', params.method);
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);

    const qs = searchParams.toString();
    const url = qs ? `${API_BASE}/gaps?${qs}` : `${API_BASE}/gaps`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch research gaps');
    return res.json();
  },

  updateGap: async (
    gapId: string,
    data: { status?: string; title?: string; description?: string; suggested_direction?: string }
  ): Promise<ResearchGapItem> => {
    const res = await fetch(`${API_BASE}/gaps/${gapId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to update research gap' }));
      throw new Error(err.detail || 'Failed to update research gap');
    }
    return res.json();
  },

  deleteGap: async (gapId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/gaps/${gapId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete research gap');
  },

  // ---------------------------------------------------------------------------
  // 8. Evidence Verification Agent
  // ---------------------------------------------------------------------------
  verifyClaim: async (claimText: string, paperId: string): Promise<VerificationResultItem> => {
    const res = await fetch(`${API_BASE}/verification/verify-claim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        claim_text: claimText,
        paper_id: paperId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Verification failed' }));
      throw new Error(err.detail || 'Failed to verify claim');
    }
    return res.json();
  },

  batchVerifyClaims: async (claims: Array<{ claim_text: string; paper_id: string }>): Promise<{
    total_claims: number;
    verified_count: number;
    contradicted_count: number;
    results: VerificationResultItem[];
  }> => {
    const res = await fetch(`${API_BASE}/verification/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claims }),
    });
    if (!res.ok) throw new Error('Batch verification failed');
    return res.json();
  },

  getVerificationHistory: async (paperId?: string): Promise<VerificationResultItem[]> => {
    const url = paperId
      ? `${API_BASE}/verification/history?paper_id=${paperId}`
      : `${API_BASE}/verification/history`;
    const res = await fetch(url);
    if (!res.ok) return [];
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 9. Cross-Paper Comparison Agent
  // ---------------------------------------------------------------------------
  comparePapers: async (paperIds: string[]): Promise<any> => {
    const res = await fetch(`${API_BASE}/comparison/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paper_ids: paperIds }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Comparison failed' }));
      throw new Error(err.detail || 'Failed to compare papers');
    }
    return res.json();
  },

  getComparisonById: async (comparisonId: string): Promise<CrossPaperComparisonReport> => {
    const res = await fetch(`${API_BASE}/comparison/${comparisonId}`);
    if (!res.ok) throw new Error('Failed to retrieve comparison report');
    return res.json();
  },

  getProjectComparisons: async (projectId: string): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/comparison/project/${projectId}`);
    if (!res.ok) throw new Error('Failed to retrieve project comparisons');
    return res.json();
  },

  getComparisonMarkdown: async (comparisonId: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/comparison/${comparisonId}/markdown`);
    if (!res.ok) throw new Error('Failed to retrieve comparison markdown');
    return res.text();
  },

  // ---------------------------------------------------------------------------
  // 10. Multi-Agent Orchestrator
  // ---------------------------------------------------------------------------
  getWorkflowStages: async (): Promise<Array<{ stage_id: string; stage_name: string; agent_name: string }>> => {
    const res = await fetch(`${API_BASE}/orchestrator/stages`);
    if (!res.ok) return [];
    return res.json();
  },

  startWorkflow: async (req: WorkflowRunRequest): Promise<WorkflowStatusResponse> => {
    const res = await fetch(`${API_BASE}/orchestrator/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to initiate workflow' }));
      throw new Error(err.detail || 'Failed to initiate workflow');
    }
    return res.json();
  },

  getWorkflowStatus: async (workflowId: string): Promise<WorkflowStatusResponse> => {
    const res = await fetch(`${API_BASE}/orchestrator/status/${workflowId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch status' }));
      throw new Error(err.detail || 'Failed to fetch workflow status');
    }
    return res.json();
  },

  resumeWorkflow: async (workflowId: string): Promise<WorkflowStatusResponse> => {
    const res = await fetch(`${API_BASE}/orchestrator/resume/${workflowId}`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to resume workflow' }));
      throw new Error(err.detail || 'Failed to resume workflow');
    }
    return res.json();
  },

  runWorkflowStage: async (req: {
    project_id: string;
    stage_id: string;
    paper_ids?: string[];
    topic?: string;
    force?: boolean;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE}/orchestrator/run-stage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to execute stage' }));
      throw new Error(err.detail || 'Failed to execute stage');
    }
    return res.json();
  },

  getWorkflowHistory: async (): Promise<WorkflowHistoryItem[]> => {
    const res = await fetch(`${API_BASE}/orchestrator/history`);
    if (!res.ok) return [];
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 11. Module A: Contradiction Detection Agent
  // ---------------------------------------------------------------------------
  detectContradictions: async (req: DetectContradictionsRequest): Promise<DetectContradictionsResponse> => {
    const res = await fetch(`${API_BASE}/contradictions/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to detect contradictions' }));
      throw new Error(err.detail || 'Failed to detect contradictions');
    }
    return res.json();
  },

  getProjectContradictions: async (
    projectId: string,
    filters?: { category?: string; nature?: string }
  ): Promise<DetectContradictionsResponse> => {
    const params = new URLSearchParams();
    if (filters?.category) params.append('category', filters.category);
    if (filters?.nature) params.append('nature', filters.nature);

    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/contradictions/project/${projectId}${qs}`);
    if (!res.ok) throw new Error('Failed to fetch project contradictions');
    return res.json();
  },

  getContradictionById: async (contradictionId: string): Promise<ContradictionItem> => {
    const res = await fetch(`${API_BASE}/contradictions/${contradictionId}`);
    if (!res.ok) throw new Error('Failed to fetch contradiction details');
    return res.json();
  },

  deleteContradiction: async (contradictionId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/contradictions/${contradictionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete contradiction');
  },

  // ---------------------------------------------------------------------------
  // 12. Module B: Research Trend Analysis
  // ---------------------------------------------------------------------------
  getCorpusTrends: async (): Promise<ResearchTrendsResponse> => {
    const res = await fetch(`${API_BASE}/trends/overview`);
    if (!res.ok) throw new Error('Failed to fetch literature corpus trends');
    return res.json();
  },

  getProjectTrends: async (projectId: string): Promise<ResearchTrendsResponse> => {
    const res = await fetch(`${API_BASE}/trends/project/${projectId}`);
    if (!res.ok) throw new Error('Failed to fetch project research trends');
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 13. Paper Discovery Agent
  // ---------------------------------------------------------------------------
  discoverPapers: async (req: DiscoverySearchRequest): Promise<DiscoverySearchResponse> => {
    const res = await fetch(`${API_BASE}/discovery/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Search failed' }));
      throw new Error(err.detail || 'Failed to search academic literature');
    }
    return res.json();
  },

  addDiscoveredPaper: async (req: AddPaperToProjectRequest): Promise<AddPaperToProjectResponse> => {
    const res = await fetch(`${API_BASE}/discovery/add-to-project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to add paper' }));
      throw new Error(err.detail || 'Failed to add paper to project');
    }
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 14. Research Paper Analysis Agent
  // ---------------------------------------------------------------------------
  getPaperAnalysis: async (paperId: string, regenerate = false): Promise<ResearchAnalysisReport> => {
    const res = await fetch(`${API_BASE}/analysis/report/${paperId}?regenerate=${regenerate}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch analysis' }));
      throw new Error(err.detail || 'Failed to fetch paper analysis report');
    }
    return res.json();
  },

  getPaperAnalysisMarkdown: async (paperId: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/analysis/report/${paperId}/markdown`);
    if (!res.ok) throw new Error('Failed to fetch markdown analysis');
    return res.text();
  },

  // ---------------------------------------------------------------------------
  // 15. Research Reports & Dossiers (Report Generator Engine)
  // ---------------------------------------------------------------------------
  getGeneratedReports: async (projectId?: string): Promise<GeneratedReportItem[]> => {
    const url = projectId
      ? `${API_BASE}/reports/history?project_id=${projectId}`
      : `${API_BASE}/reports/history`;
    const res = await fetch(url);
    if (!res.ok) return [];
    return res.json();
  },

  generateAcademicReport: async (req: ReportGenerateRequest): Promise<ReportDetailResponse> => {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to generate report' }));
      throw new Error(err.detail || 'Report generation failed');
    }
    return res.json();
  },

  getReportsHistory: async (projectId?: string): Promise<ReportSummaryItem[]> => {
    const url = projectId
      ? `${API_BASE}/reports/history?project_id=${projectId}`
      : `${API_BASE}/reports/history`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch reports history');
    return res.json();
  },

  getReportDetail: async (reportId: string): Promise<ReportDetailResponse> => {
    const res = await fetch(`${API_BASE}/reports/${reportId}`);
    if (!res.ok) throw new Error('Failed to fetch report details');
    return res.json();
  },

  exportReportFile: async (reportId: string, format: 'pdf' | 'docx' | 'markdown', defaultFilename?: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/reports/${reportId}/export/${format}`);
    if (!res.ok) {
      throw new Error(`Failed to export report as ${format.toUpperCase()}`);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ext = format === 'markdown' ? 'md' : format;
    a.download = defaultFilename ? `${defaultFilename}.${ext}` : `research_report_${reportId.slice(0, 8)}.${ext}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  deleteReport: async (reportId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete report');
  },

  // ---------------------------------------------------------------------------
  // 16. System Health, Diagnostics & Configuration Engine
  // ---------------------------------------------------------------------------
  getSystemStatus: async (): Promise<CompleteSystemStatus> => {
    const res = await fetch(`${API_BASE}/system/status`);
    if (!res.ok) throw new Error('Failed to fetch detailed system status');
    return res.json();
  },

  getSystemConfig: async (): Promise<SystemConfig> => {
    const res = await fetch(`${API_BASE}/system/config`);
    if (!res.ok) throw new Error('Failed to fetch system configuration');
    return res.json();
  },

  updateSystemConfig: async (config: SystemConfigUpdate): Promise<SystemConfig> => {
    const res = await fetch(`${API_BASE}/system/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Configuration validation failed' }));
      let msg = err.detail;
      if (Array.isArray(err.detail)) {
        msg = err.detail.map((d: any) => d.msg).join(', ');
      }
      throw new Error(msg || 'Configuration update rejected');
    }
    return res.json();
  },

  selectActiveModels: async (req: { llm_model: string; embed_model?: string }): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/models/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error('Failed to update active model selection');
    return res.json();
  },

  testOllamaPing: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/test/ollama`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to test Ollama connection');
    return res.json();
  },

  testEmbeddingGen: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/test/embedding`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to test embedding generation');
    return res.json();
  },

  testDatabases: async (): Promise<DatabaseTestResponse> => {
    const res = await fetch(`${API_BASE}/system/test/databases`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to check database connections');
    return res.json();
  },

  runSystemDiagnostics: async (): Promise<SystemDiagnosticsResponse> => {
    const res = await fetch(`${API_BASE}/system/diagnostics`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to run system diagnostics sweep');
    return res.json();
  },

  getAgentExecutionLogs: async (params?: {
    agent_name?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<AgentLogsResponse> => {
    const q = new URLSearchParams();
    if (params?.agent_name) q.append('agent_name', params.agent_name);
    if (params?.status) q.append('status', params.status);
    if (params?.limit) q.append('limit', String(params.limit));
    if (params?.offset) q.append('offset', String(params.offset));

    const qs = q.toString() ? `?${q.toString()}` : '';
    const res = await fetch(`${API_BASE}/system/agent-logs${qs}`);
    if (!res.ok) throw new Error('Failed to fetch agent execution logs');
    return res.json();
  },

  pingFrontendConnection: async (): Promise<{ latency_ms: number; status: string }> => {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/health`);
      const latency_ms = Math.round((performance.now() - start) * 10) / 10;
      return {
        latency_ms,
        status: res.ok ? 'connected' : 'error',
      };
    } catch {
      return {
        latency_ms: Math.round((performance.now() - start) * 10) / 10,
        status: 'disconnected',
      };
    }
  },
};
